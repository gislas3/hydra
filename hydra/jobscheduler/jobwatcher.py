import logging
import time

from django.conf import settings
from distutils import util
import threading
import json
from kubernetes import client, config, utils, watch
import kubernetes.client
from kubernetes.client.models.v1_job import V1Job
from kubernetes.client.rest import ApiException
from urllib3.exceptions import InvalidChunkLength

from api.models import Batch_Job
from django.core.exceptions import ObjectDoesNotExist
from hydra.jobmanager import jobmanager


class JobWatcher():
    def __init__(self, jobscheduler, api_instance, core_api_instance):
        self.jobscheduler = jobscheduler
        self.api_instance = api_instance
        self.core_api_instance = core_api_instance
        self.watch_namespace = settings.WATCH_K8S_NAMESPACE
        # Watch k8s
        if hasattr(settings, "WATCH_K8S"):
            WATCH_K8S = util.strtobool(str(settings.WATCH_K8S))
            if (WATCH_K8S):
                thread = threading.Thread(target=self.watch_jobs_events, args=())
                thread.daemon = True
                thread.start()

    def watch_jobs_events(self):
        watch_params = {
            "namespace": self.watch_namespace,
            "timeout_seconds": settings.WATCH_K8S_TIMEOUT,
            "_request_timeout": settings.WATCH_K8S_REQUEST_TIMEOUT,
            "pretty": True
         }
        watch_namespace = watch_params["namespace"]
        # This isnt the most elegant, but sometimes it seems that w.stream() looses connection to the k8s cluster and
        # raised InvalidChunkLength exception. Catching this here and then restarting the for-loop
        # more info here: https://github.com/kubernetes-client/python/issues?q=invalid+literal+for+int%28%29+with+base+16%3A+b%27
        self.jobmanager = jobmanager.JobManager()
        while True:
            logging.info("Watching k8s for job updates in '%s' namespace", watch_namespace,extra={"watch_params": json.dumps(watch_params)})
            w = watch.Watch()
            job_events_stream = w.stream(self.api_instance.list_namespaced_job, **watch_params)
            try:
                for event in job_events_stream:
                    job_name = event['object'].metadata.name
                    resource_version = event['object'].metadata.resource_version
                    #logging.info("Event: %s %s %s status: %s" % (event['type'], event['object'].kind, job_name, event["object"].status.active))
                    batch_job_id = job_name.split("-")[-1]
                    try:
                        batch_job = Batch_Job.objects.get(id=batch_job_id)
                    except ObjectDoesNotExist:
                        logging.info("Batch_Job with id: '%s' does not exists in the database", str(batch_job_id))
                        continue
                    batch_ids = [str(b.batch_id) for b in batch_job.batches.all()]
                    if event['type'] == "ADDED":
                        # make sure we only do this a single time
                        if batch_job.started == False:
                            self.job_is_created(job_name, batch_job, batch_job_id,batch_ids)
                    elif event['type'] == "MODIFIED":
                        # if job is still running but failing
                        if event["object"].status.failed == None:
                            event["object"].status.failed = 0
                        # The job is created on k8s but not able to start or restarts
                        if event["object"].status.active == 1 and event["object"].status.failed > 0:
                            self.job_is_failing(event, job_name, batch_job, batch_job_id, batch_ids)
                        elif event["object"].status.active == 1 and event["object"].status.succeeded == None:
                            self.job_is_running(event, job_name, batch_job, batch_job_id, batch_ids)
                        # if job is inactive (done running) and succeded and exists in k8s (sometimes the same k8s event is raised twice)
                        elif event["object"].status.active == None and event["object"].status.succeeded == 1 and self.jobscheduler.kube_does_job_exist(job_name,watch_namespace):
                            self.job_is_completed(event,job_name,batch_job,batch_job_id,batch_ids)
            except ValueError as e:
                logging.error("lost connection to k8s, due to 'ValueError', restarting k8s watcher",
                  extra={
                      "exception": str(e),
                      "batch_job_id": batch_job_id if batch_job_id is not None else "None",
                      "k8s_resource_version": resource_version
                    }
                  )
            except InvalidChunkLength as e:
                logging.error("lost connection to k8s, due to 'InvalidChunkLength', restarting k8s watcher",
                  extra={
                      "exception": str(e),
                      "batch_job_id": batch_job_id if batch_job_id is not None else "None",
                      "k8s_resource_version": resource_version
                    }
                  )
            except Exception as e:
                logging.error("lost connection to k8s, due to 'Exception', restarting k8s watcher",
                  extra={
                      "exception": str(e),
                      "batch_job_id": batch_job_id if batch_job_id is not None else "None",
                      "k8s_resource_version": resource_version
                    }
                )
            finally:
                # we delete these two, to make sure we get a new connection to the k8s cluster
                del w
                del job_events_stream
                time.sleep(2)



    def get_namespaced_pod_name(self, namespace, label_selector):
        pod_name = None
        logging.debug("Looking for pod in %s namespace with label-selector '%s'", namespace, label_selector)
        try:
            api_response = self.core_api_instance.list_namespaced_pod(namespace, pretty=True, label_selector=label_selector)
            pod_name = api_response.items[0].metadata.name
        except ApiException as e:
            print("Exception when calling CoreV1Api->list_namespaced_pod: '%s'\n" % e)
        return pod_name


    def get_pod_status(self, name, namespace):
        pod_status = None
        try:
            api_response = self.core_api_instance.read_namespaced_pod_status(name, namespace, pretty=True)
            pod_status = api_response.status.phase
        except ApiException as e:
            print("Exception when calling CoreV1Api->read_namespaced_pod_status: '%s'\n" % e)
        return pod_status


    def job_is_created(self, job_name, batch_job, batch_job_id, batch_ids):
        logging.info("Created k8s job: '%s'", job_name,
                     extra={"batch_job_id": batch_job_id,
                            "job_name": job_name,
                            "pod_failures": "0",
                            "batches": batch_ids})
        self.jobmanager.on_job_created(batch_job)

    def job_is_failing(self,event, job_name, batch_job, batch_job_id, batch_ids):
        pod_failure_count = event["object"].status.failed
        pod_name = self.get_namespaced_pod_name(self.watch_namespace, "job-name=" + job_name)
        pod_status = self.get_pod_status(pod_name, self.watch_namespace)
        logging.warning("Failed pod %s in Hydra k8s job: '%s'", pod_name, job_name,
                        extra={"batch_job_id": batch_job_id,
                               "job_name": job_name,
                               "pod_failures": str(pod_failure_count),
                               "pod_status": pod_status,
                               "batches": batch_ids})
        self.jobmanager.on_job_failure(batch_job, pod_failure_count)

    def job_is_running(self,event, job_name, batch_job, batch_job_id, batch_ids):
        # set the job to be started
        start_time = event["object"].metadata.creation_timestamp
        logging.info("Running k8s job: '%s'", job_name,
                     extra={"batch_job_id": batch_job_id,
                            "job_name": job_name,
                            "batches": batch_ids})
        self.jobmanager.on_job_started(batch_job, start_time)

    def job_is_completed(self,event, job_name, batch_job, batch_job_id, batch_ids):
        completion_time = event["object"].status.completion_time
        logging.info("Completed Hydra k8s job: '%s'", job_name,
                     extra={"batch_job_id": batch_job_id,
                            "job_name": job_name,
                            "completion_time": completion_time,
                            "batches": batch_ids})
        self.jobmanager.on_job_success(batch_job)
        self.jobscheduler.kube_delete_job(job_name, self.watch_namespace)