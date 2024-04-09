
# INSPIRATION
# https://kubernetes-job.readthedocs.io/en/latest/kubernetes.html#the-kubernetes-job-spec-template-e-g-job-yaml
# https://blog.pythian.com/how-to-create-kubernetes-jobs-with-python/

from api.models import Batch_Job
from os import name
from api.views import ApiOverview
import logging
import tempfile
import base64
import json
import asyncio
import sys
from kubernetes import client, config, utils, watch
import kubernetes.client
from kubernetes.client.models.v1_job import V1Job
from kubernetes.client.rest import ApiException
from django.conf import settings
from distutils import util
import threading
from hydra.jobscheduler.jobwatcher import JobWatcher

import time
class JobScheduler(object):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logging.debug("Creating the JobScheduler singleton", extra={})
            cls._instance = super(JobScheduler, cls).__new__(cls)
            cls._instance._init_instance()
            # Put any initialization here.
        return cls._instance
    def _init_instance(self):
        """
            Constructs a new job scheduler for creating and deleting jobs on
            a k8s cluster
        """

        # retrieve cluster details from environment variables
        host_url = settings.K8S_API_URL
        cacert = settings.K8S_CACERT
        token = settings.K8S_TOKEN

        configuration = None

        if host_url:
            # initialize configuration for token authentication
            # this is the way to go if we're using a service account
            configuration = client.Configuration()
            configuration.api_key["authorization"] = token
            configuration.api_key_prefix['authorization'] = 'Bearer'
            configuration.host = host_url

            # configuration.ssl_ca_cert expects a file containing the
            # certificates,so we generate a temporary file to hold those
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
                tf.write(base64.b64decode(cacert).decode("utf-8"))
                configuration.ssl_ca_cert = tf.name

        else:
            # try to initialize from $HOME/.kube/config (eg. kubectl config)
            logging.info("Loading k8s from file-system")
            config.load_kube_config()

        # initialize the Kubernetes client
        kubernetes.client.rest.logger.setLevel(logging.INFO)
        self.api_instance = kubernetes.client.BatchV1Api(kubernetes.client.ApiClient(configuration))
        self.core_api_instance = kubernetes.client.CoreV1Api(kubernetes.client.ApiClient(configuration))

        # Testing Credentials
        self.kube_test_credentials()

        # Create k8s watcher
        jobwatcher = JobWatcher(self, self.api_instance, self.core_api_instance)

    def kube_cleanup_jobs_with_state(self, namespace='processing', state='Finished', jobs_label_selector=""):
        """
        Since the TTL flag (ttl_seconds_after_finished) is still in alpha
        (Kubernetes 1.12) jobs need to be cleanup manually
        As such this method checks for existing Finished Jobs and deletes them.

        By default it only cleans Finished jobs. Failed jobs require manual
        intervention or a second call to this function.

        Docs: https://kubernetes.io/docs/concepts/workloads/controllers/jobs-run-to-completion/#clean-up-finished-jobs-automatically

        For deletion you need a new object type! V1DeleteOptions! But you can
        have it empty!

        CAUTION: Pods are not deleted at the moment. They are set to not
                 running, but will count for your autoscaling limit, so if
                 pods are not deleted, the cluster can hit the autoscaling
                 limit even with free, idling pods.
                 To delete pods, at this moment the best choice is to use the
                 kubectl tool
                 ex: kubectl delete jobs/JOBNAME.
                 But! If you already deleted the job via this API call, you
                 now need to delete the Pod using Kubectl:
                 ex: kubectl delete pods/PODNAME
        """
        deleteoptions = client.V1DeleteOptions()
        try:
            jobs = self.api_instance.list_namespaced_job(
                namespace,
                label_selector=jobs_label_selector,
                pretty=True,
                timeout_seconds=60
            )
        except ApiException as e:
            logging.warning(
                "Exception when calling BatchV1Api->list_namespaced_job",
                extra={
                    "exception": e,
                }
            )

        # Now we have all the jobs, lets clean up
        # We are also logging the jobs we didn't clean up because they either
        # failed or are still running
        deleted_job_names = []
        for job in jobs.items:
            jobname = job.metadata.name
            jobstatus = job.status.conditions
            job_state = None
            if job.status.succeeded == 1 and state == "Finished":
                #logging.info("Deleting finished job")
                self.kube_delete_job(jobname,namespace)
                deleted_job_names.append(jobname)
            elif jobstatus is None and job.status.active == 1 and state == "Active":
                #logging.info("Deleting active job")
                self.kube_delete_job(jobname,namespace)
                deleted_job_names.append(jobname)

        return deleted_job_names

    def kube_create_job_object(
        self,
        name,
        container_image,
        namespace="processing",
        container_name="jobcontainer",
        init_photo_container=False,
        labels={},
        env_vars={}
    ):
        """
        Create a k8 Job Object
        Minimum definition of a job object:
        {'api_version': None, - Str
        'kind': None,     - Str
        'metadata': None, - Metada Object
        'spec': None,     -V1JobSpec
        'status': None}   - V1Job Status
        Docs: https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1Job.md
        Docs2: https://kubernetes.io/docs/concepts/workloads/controllers/jobs-run-to-completion/#writing-a-job-spec
        Docs3: https://github.com/kubernetes-client/python

        Also docs are pretty pretty bad. Best way is to
        ´pip install kubernetes´ and go via the autogenerated code
        And figure out the chain of objects that you need to hold a final valid
        object So for a job object you need:
        V1Job -> V1ObjectMeta
            -> V1JobStatus
            -> V1JobSpec -> V1PodTemplate -> V1PodTemplateSpec -> V1Container

        Now the tricky part, is that V1Job.spec needs a .template, but not a
        PodTemplateSpec, as such you need to build a PodTemplate, add a
        template field (template.template) and make sure
        template.template.spec is now the PodSpec.
        Then, the V1Job.spec needs to be a JobSpec which has a template the
        template.template field of the PodTemplate.
        Failure to do so will trigger an API error.

        Also Containers must be a list!

        Docs3: https://github.com/kubernetes-client/python/issues/589
        """
        must_have_labels = {"name": name}

        if labels:
            must_have_labels.update(labels)

        # Body is the object Body$
        body = client.V1Job(api_version="batch/v1", kind="Job")
        # Body needs Metadata
        # Attention: Each JOB must have a different name!
        body.metadata = client.V1ObjectMeta(
            namespace=namespace,
            name=name,
            labels=must_have_labels
        )
        # And a Status
        body.status = client.V1JobStatus()
        # Now we start with the Template...
        pod_object_meta = client.V1ObjectMeta(
            annotations={
                "vault.security.banzaicloud.io/vault-addr": "https://vault.vault:8200",
                "vault.security.banzaicloud.io/vault-role": "applications",
                "vault.security.banzaicloud.io/vault-tls-secret": "vault-tls"
            }
        )
        template = client.V1PodTemplate()
        template.template = client.V1PodTemplateSpec(
            metadata=pod_object_meta
        )
        # Passing Arguments in Env:
        env_list = []
        for env_name, env_value in env_vars.items():
            env_list.append(client.V1EnvVar(name=env_name, value=env_value))
        container = client.V1Container(
            name=container_name,
            image_pull_policy="Always",
            image=container_image,
            env=env_list,
            volume_mounts=self.get_shared_volume_mount()
        )
        image_pull_secret = client.V1LocalObjectReference(
            name="gitlab-registry"
        )
        init_containers = []
        if init_photo_container:
            logging.debug(
                "Job is requesting an init_photo_container, adding now",
                extra={
                    "job": name,
                }
            )
            init_containers.append(self.get_photo_init_container(env_vars))

        shared_volume_mount = client.V1Volume(
            name="shared-pod-data",
            empty_dir={}
        )

        template.template.spec = client.V1PodSpec(
            containers=[container],
            init_containers=init_containers,
            restart_policy='Never',
            image_pull_secrets=[image_pull_secret],
            volumes=[shared_volume_mount]
        )
        # And finaly we can create our V1JobSpec!
        body.spec = client.V1JobSpec(
            ttl_seconds_after_finished=600, template=template.template)
        return body

    def get_shared_volume_mount(self):
        """
            Return list of V1VolumeMount
        """
        mount_path = "/shared-pod-data"
        mount_name = "shared-pod-data"

        return [client.V1VolumeMount(mount_path=mount_path, name=mount_name)]

    def get_photo_init_container(self, batch_id):
        container_name = "init-photo-container"
        container_image = "registry.mobilizedconstruction.com/mc/s3-image-client:latest"
        env_vars = {
            "AWS_ACCESS_KEY_ID": "vault:secret/data/hydra#AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY": "vault:secret/data/hydra#AWS_SECRET_ACCESS_KEY"
        }
        env_list = []
        for env_name, env_value in env_vars.items():
            env_list.append(client.V1EnvVar(name=env_name, value=env_value))
        logging.debug(
            "get_photo_init_container called with batch ids",
            extra={
                "batch_ids": batch_id["BATCH_IDS"],
            }
        )
        args = ["./image_client.py",
            "--batch=" + batch_id["BATCH_IDS"],
            "--download",
            "--download_dir=/shared-pod-data",
            "--sequential",
            "--print_summary"
        ]
        init_photo_container = client.V1Container(
            name=container_name,
            image=container_image,
            env=env_list,
            args=args,
            volume_mounts=self.get_shared_volume_mount()
        )
        return init_photo_container

    def kube_test_credentials(self):
        """
        Testing function.
        If you get an error on this call don't proceed. Something is wrong on
        your connectivty to k8s API.
        Check Credentials, permissions, keys, etc.
        Docs: https://cloud.google.com/docs/authentication/
        """
        try:
            api_response = self.api_instance.get_api_resources()
            logging.info("Connected to k8s using credentials!")
        except ApiException as e:
            logging.debug(
                "Test k8s credentials failed.",
                extra={
                    "response": api_response,
                    "exception": e
                }
            )
    def kube_create_job(
        self,
        job_name,
        namespace,
        env,
        container_image,
        init_photo_container=False,
        labels={}
    ):
        # Create the job
        body = self.kube_create_job_object(
            job_name,
            container_image,
            namespace,
            "jobcontainer",
            init_photo_container,
            labels,
            env_vars=env
        )
        api_response = None
        try:
            api_response = self.api_instance.create_namespaced_job(
                namespace, body, pretty=True)
        except ApiException as e:
            logging.debug(
                "Exception when calling BatchV1Api->create_namespaced_job",
                extra={
                    "exception": e,
                }
            )
            jsonException = json.loads(e.body)
            logging.info(
                "Could not create job %s . k8s errormessage: %s", job_name,jsonException["message"],
                extra={}
            )
            return jsonException["reason"]
        return api_response

    def kube_delete_job(self, job_name,namespace):
        logging.info("Deleting k8s job '%s'", job_name,
                     extra={})
        try:
            self.api_instance.delete_namespaced_job(
                job_name,
                namespace,
                grace_period_seconds=0,
                propagation_policy='Background'
            )
        except ApiException as e:
            logging.debug(
                "Exception when calling BatchV1Api->delete_namespaced_job",
                extra={
                    "exception": e,
                }
            )
            jsonException = json.loads(e.body)
            logging.info(
                "Could not delete job %s. Maybe it was already deleted?", job_name,
                extra={"exception": jsonException["message"]}
            )
        # make sure job is marked for deletion in the k8s cluster
        time.sleep(1)

    def kube_does_job_exist(self,name,namespace):
        try:
            job = self.api_instance.read_namespaced_job(name,namespace)
            if job:
                return True
        except ApiException:
            return False

    def kube_does_job_exist(self,name,namespace):
        try:
            job = self.api_instance.read_namespaced_job(name,namespace)
            if job:
                return True
        except ApiException:
            return False

    def kube_get_job_status(self, name, namespace):
        """
        Returns the status of a k8s job.
        :param name: The name of k8s job
        :param namespace: the namespace for the k8s job. Most likely 'processing'
        :return: None or 1 depending the state of the job.
        """
        api_response = None
        try:
            api_response = self.api_instance.read_namespaced_job_status(
                name, namespace, pretty=True)
        except ApiException as e:
            logging.warning(
                "Exception when calling BatchV1Api->read_namespaced_job_status",
                extra={
                    "exception": e,
                }
            )
        # json_api_response = json.loads(api_response)
        try:
            V1JobStatus = api_response.status
        except AttributeError as e:
            logging.warning(
                "Was not able to get job status. Maybe the job does not exists?",
                extra={
                    "exception": e,
                }
            )
            raise ValueError('Could not find job with this name')

        num_succeeded = V1JobStatus.succeeded
        num_failed = V1JobStatus.failed
        num_active = V1JobStatus.active
        if num_succeeded is not None and num_succeeded > 0:
            return 'succeeded'
        elif num_active is not None and num_active > 0:
            return 'active'
        elif num_failed is not None and num_failed > 0: 
            return 'failed'
        else:
            return "non-succeeded"
