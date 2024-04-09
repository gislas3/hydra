import datetime as dt
import sys
import logging
import uuid
import os
from api.models import Job_Spec
from api.models import Batch_Job
from hydra.jobscheduler import jobscheduler
from django.conf import settings

class JobManager(object):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logging.debug("Creating the JobManager singleton", extra={})
            cls._instance = super(JobManager, cls).__new__(cls)
            cls._instance._init_instance()
            # Put any initialization here.
        return cls._instance

    def _init_instance(self):
        """
        Class that defines methods and state of new JobManager.
        :param max_active_jobs: The maximum number of active jobs that this JobManager should allow to be running simultaneously
        """
        # Note: data_type should be a static variable defined in each subclass instance of jobmanager

        self.max_active_jobs = int(settings.MAX_ACTIVE_K8S_JOBS)
        self.active_jobs = 0
        try:
            self.job_scheduler = jobscheduler.JobScheduler()
        except Exception as e:
            logging.error("Failed to create jobscheduler, quitting JobManager", extra={"Exception": e})
            sys.exit(1)

    def make_kubernetes_job_name(self, batch_job):
        """
        Creates the job name from the batch_job, which is just the job definition name + the batch_job id.
        :param batch_job: Should be an instance of `Batch_Job`.
        """
        jspec = batch_job.job_spec
        return "{0}-{1}".format(jspec.job_definition.name, batch_job.id)

    def on_add_batch_event(self, batch, parent_job=None):
        """
        Defines the general behavior for responding to an add batch event.
        :param batch_data: Should be an instance of `Batch`. Information about the current batch.
        :param parent_job: Should be an instance of `Job_Definition` or None. The parent job that has been completed, if any.
        """


        # Get all active job specs associated with this parent job
        job_specs = Job_Spec.objects.filter(active=True, job_definition__parent_job=parent_job).order_by(
            '-priority')  # TODO: Add other possible filters

        # Notify all observers (all jobs which are interested in this batch of data)
        for j_spec in job_specs:
            # Check for devices here 
            whitelisted_devices = j_spec.whitelisted_devices
            if whitelisted_devices is not None and len(whitelisted_devices) > 0:
                try:
                    whitelisted_devices = set(map(lambda x: uuid.UUID(x), whitelisted_devices))
                except Exception as e:
                    logging.warning("INVALID DEVICES SPECIFIED, WHITELISTED DEVICES WILL BE IGNORED!!!", extra={'whitelisted_devices': whitelisted_devices})
            elif whitelisted_devices is None:
                whitelisted_devices = []
            device_id = batch.device_id
            if (device_id and device_id in whitelisted_devices) or not device_id or len(whitelisted_devices) == 0:
                # Only add batch to job and decide job if:
                # There is a device and it is in the whitelisted devices, there is no device_id, or there are no whitelisted devices
                batch_job_to_decide = self.add_batch_to_job(j_spec, batch)
                # Decide whether or not to run the job
                self.decide_job(batch_job_to_decide)

    def on_save_batch_job_event(self, batch_job):
        """
        Method which should be called when a `Batch_Job` is saved, i.e. its state has changed. Should be overridden in
        a subclass.
        :param batch_job: The instance `Batch_Job` that was saved.
        """
        if batch_job.finished and batch_job.succeeded:  # only want to do something if the batch job completed successfully
            for batch in batch_job.batches.all():
                self.on_add_batch_event(batch,
                                        parent_job=batch_job.job_spec.job_definition)

    def add_batch_to_job(self, job_spec, batch):
        """
        This method should be overridden in a subclass. In effect, will add a Batch to a kubernetes job.
        """
        curr_batch_job = None
        # TODO: More data integrity checks to account for possible race conditions?
        # Look at all unstarted jobs
        for cand_batch_job in job_spec.batch_job_set.filter(scheduled=False):
            # Make sure this job doesn't have too much data added to it already
            # GI: Criteria based on number of batches
            if cand_batch_job.batches.count() < job_spec.data_threshold:
                curr_batch_job = cand_batch_job
            else:  # If job already has enough data to be run, see if it should be run
                self.decide_job(cand_batch_job)
        if curr_batch_job is None:  # Didn't find a Batch_Job to add the batch to, so create a new one
            curr_batch_job = Batch_Job.objects.create(job_spec=job_spec)
        curr_batch_job.batches.add(batch)
        curr_batch_job.save()
        return curr_batch_job

    def decide_job(self, job_to_decide):
        """
        This method should be overridden in a subclass - will determine whether or not to trigger a job.
        """
        if self.active_jobs < self.max_active_jobs and job_to_decide.batches.count() >= job_to_decide.job_spec.data_threshold:
            self.start_job(job_to_decide)

    def start_job(self, batch_job):
        """
        Defines the general behavior that should be done whenever a job is started. Basically, this is just adding the job information
        to the database.
        :param k_job: Should be an instance of `Kube_Job`, defines the job (or metadata about the job if you prefer) that will be started.
        """
        batch_job.scheduled = True
        batch_job.save()
        self.active_jobs += 1
        batch_ids = []
        for batch in batch_job.batches.all():
            batch_id = str(batch.batch_id)
            logging.debug("Adding batch to batches:" + batch_id)
            batch_ids.append(batch_id)
        logging.debug("Starting Job with batches: " + str(batch_ids))
        # logging.info("{0}, {1}, {2}, {3}".format(self.make_kubernetes_job_name(batch_job), batch_job.job_spec.namespace, {'BATCH_IDS': ','.join(batch_ids)}, batch_job.job_spec.container_image))
        job_spec = batch_job.job_spec
        job_name = self.make_kubernetes_job_name(batch_job)
        k8s_labels = batch_job.job_spec.k8s_job_labels
        try:
            self.job_scheduler.kube_create_job(job_name, job_spec.namespace, self.get_env_vars(batch_job, batch_ids),
                                               job_spec.container_image, init_photo_container=job_spec.init_photo_container, labels=k8s_labels)
        except Exception as e:
            logging.warning("Job {0} was unable to be created".format(
                job_name), extra={'job_name': job_name, 'exception': e})

        # Defines the job to be done for the instance of the class
    def on_job_failure(self, batch_job, job_tries):
        """
        Defines the general behavior that should be done whenever a job fails. Basically, this is just adding the failure information to the database.
        :param k_job: Should be an instance of `Kube_Job`, defines the job (or metadata about the job if you prefer) that will be started.
        :param job_tries: A optional argument that specified the number of (re)tries for a specific k_job
        """

        batch_job.tries = job_tries
        self.active_jobs = max(self.active_jobs - 1, 0)
        batch_job.save()
        job_name = self.make_kubernetes_job_name(batch_job)
        logging.debug("Job {0} was marked as failed".format(
            job_name), extra={'job_name': job_name})

    def on_job_success(self, batch_job):
        """
        Defines the general behavior that should be done whenever a job succeeds Basically, this is just adding the success information to the database.
        :param k_job: Should be an instance of `Kube_Job`, defines the job (or metadata about the job if you prefer) that will be started.
        """
        batch_job.finished = True
        batch_job.succeeded = True
        self.active_jobs = max(self.active_jobs - 1, 0)
        batch_job.save()

    def on_job_created(self, batch_job):
        """
        Defines the general behavior that should be done whenever a job is created as a k8s object, but not yet running a pod.
        :param k_job: Should be an instance of `Kube_Job`, defines the job (or metadata about the job if you prefer) that will be started.
        """
        batch_job.started = False
        batch_job.created_on_k8s = True
        batch_job.save()

    def on_job_started(self, batch_job, start_time):
        """
        Defines the general behavior that should be done whenever a job is created as a k8s object AND have a running k8s pod.
        :param k_job: Should be an instance of `Kube_Job`, defines the job (or metadata about the job if you prefer) that will be started.
        """
        batch_job.started = True
        batch_job.succeeded = False
        batch_job.finished = False
        batch_job.time_started = start_time
        batch_job.tries = 0
        batch_job.save()

    def get_env_vars(self, batch_job, batch_ids):
        environment_variables = batch_job.job_spec.environment_variables
        batch_dict = {'BATCH_IDS': ','.join(batch_ids)}
        if not environment_variables:
            return batch_dict
        environment_variables.update(batch_dict)
        return environment_variables
