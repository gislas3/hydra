import datetime as dt
import time
import logging
import json
import string
import random
from django.test import TestCase, TransactionTestCase
from unittest.mock import patch
from rest_framework.test import APIClient
from django.test import Client
from django.urls import reverse

from api.models import Job_Spec, Batch_Job
from api.models import Job_Definition
from hydra.jobscheduler.jobscheduler import JobScheduler

class BasicPhotoGeneratorTestCases(TransactionTestCase):
    # Since we are relying on specific PK id's, we need to reset id's between tests
    # More info here: https://docs.djangoproject.com/en/dev/topics/testing/advanced/#django.test.TransactionTestCase.reset_sequences
    reset_sequences = True
    _job_name = None

    def setUp(self):
        self.region_code = "EU.CARDIFF"
        self.job_name = "test-thread-photo-to-video"
        self.namespace = "processing-test"
        self.test_photo_jd = Job_Definition.objects.create(name=self.job_name,
                                                           description="testjobmanager for creating videos", parent_job=None)

        self.photo_job_spec1 = Job_Spec.objects.create(
            job_definition=self.test_photo_jd,
            run_environment='k8s',
            container_image="registry.mobilizedconstruction.com/mc/s3-image-client/generate-video",
            time_limit=dt.timedelta(hours=1),
            data_threshold=1,
            namespace=self.namespace,
            init_photo_container=True,
            trigger_children=False,
            environment_variables={
                "OUTPUT_NAME": "created-for-test.mp4",
                "AWS_ACCESS_KEY_ID": "vault:secret/data/hydra#AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY": "vault:secret/data/hydra#AWS_SECRET_ACCESS_KEY",
            },
            k8s_job_labels={"created-for-basic-photo-test": "true"})

        self.api_client = APIClient()

    def tearDown(self):
        jobscheduler = JobScheduler()
        jobscheduler.kube_cleanup_jobs_with_state(
            namespace="processing-test",
            state="Active",
            jobs_label_selector="created-for-basic-photo-test=true"
        )
        jobscheduler.kube_cleanup_jobs_with_state(
            namespace="processing-test",
            state="Finished",
            jobs_label_selector="created-for-basic-photo-test=true"
        )
        # make sure the job(s) is deleted before running next test
        time.sleep(2)

    def get_kubernetes_job_name(self, batch_job):
        to_ret = "{0}-{1}".format(batch_job.job_spec.job_definition.name, batch_job.id)
        return to_ret


    def test_create_job_and_run_with_success(self):
        batch_pk = 1
        batch_id = "b508b649-7691-4775-936b-91a6c8ac702b"
        good_response = self.post_batch(batch_id)
        if good_response.status_code != 201:
            logging.info("API RESPONSE: " + str(good_response.data))
            assert False
        time.sleep(30)
        batch_job = Batch_Job.objects.get(id=batch_pk)
        self.assertTrue(batch_job.finished)
        self.assertTrue(batch_job.succeeded)

    def test_that_job_is_created(self):
        batch_pk = 1
        batch_id = "b508b649-7691-4775-936b-91a6c8ac702b"
        good_response = self.post_batch(batch_id)
        if good_response.status_code != 201:
            logging.info("API RESPONSE: " + str(good_response.data))
            assert False
        time.sleep(3)
        job_scheduler = JobScheduler()
        batch_job = Batch_Job.objects.get(id=batch_pk)
        job_name = self.get_kubernetes_job_name(batch_job)
        job_exists = job_scheduler.kube_does_job_exist(job_name, "processing-test")
        self.assertTrue(job_exists)
        self.assertTrue(batch_job.scheduled)
        self.assertFalse(batch_job.finished)

    def test_that_successful_job_is_cleaned_up(self):
        batch_pk = 1
        batch_id = "b508b649-7691-4775-936b-91a6c8ac702b"
        good_response = self.post_batch(batch_id)
        if good_response.status_code != 201:
            logging.info("API RESPONSE: " + str(good_response.data))
            assert False
        time.sleep(3)
        job_scheduler = JobScheduler()
        batch_job = Batch_Job.objects.get(id=batch_pk)
        job_name = self.get_kubernetes_job_name(batch_job)
        job_exists = job_scheduler.kube_does_job_exist(job_name, "processing-test")
        self.assertTrue(job_exists)
        time.sleep(20)
        job_scheduler = JobScheduler()
        batch_job = Batch_Job.objects.get(id=batch_pk)
        job_name = self.get_kubernetes_job_name(batch_job)
        job_exists = job_scheduler.kube_does_job_exist(job_name, "processing-test")
        self.assertTrue(batch_job.finished)
        self.assertTrue(batch_job.succeeded)
        self.assertFalse(job_exists)

    def test_run_video_generator_with_env_vars(self):
        batch_pk = 1
        batch_id = "b508b649-7691-4775-936b-91a6c8ac702b"
        good_response = self.post_batch(batch_id)
        if good_response.status_code != 201:
            logging.info("API RESPONSE: " + str(good_response.data))
            assert False
        batch_job = Batch_Job.objects.get(id=batch_pk)
        self.assertTrue(batch_job.scheduled)
        time.sleep(20)
        batch_job = Batch_Job.objects.get(id=batch_pk)
        self.assertEqual(True, batch_job.started)
        # wait for job to complete
        time.sleep(20)
        # because of threading we need to fetch the object from the database again
        batch_job = Batch_Job.objects.get(id=batch_pk)
        self.assertTrue(batch_job.finished)
        self.assertTrue(batch_job.succeeded)


    def test_number_of_retries_is_updated(self):
        """
         Using a batch id that does not exist, causes the k8s job to be created but unable to run.
         This should mean that the number of retries should be grater than 1
        """
        batch_pk = 1
        none_existing_batch_id = "b508b649-7691-4775-936b-91a6c8ac111c"
        good_response = self.post_batch(none_existing_batch_id)
        if good_response.status_code != 201:
            logging.info("API RESPONSE: " + str(good_response.data))
            assert False
        batch_job = Batch_Job.objects.get(id=batch_pk)
        self.assertEqual(0, batch_job.tries)
        time.sleep(25)
        batch_job = Batch_Job.objects.get(id=batch_pk)
        self.assertGreater(batch_job.tries, 1)

    
    def setup_region(self):
        url = "/api/regions/"
        #url = reverse('regions-list')
        valid_data = {"code": self.region_code,
                      "description": "CARDIFF", "namespace": "processing-test"}
        res = self.api_client.post(url, valid_data)
        if res.status_code != 200:
            logging.info("API RESPONSE: " + str(res.data))

    def post_batch(self, batch_id):
        self.batch_id = batch_id

        self.num_photos = "1000"
        self.file_number = "5"

        # setup region
        self.setup_region()
       # self.jobscheduler = JobScheduler()

        batch_photo_data = {
            "batch_id": self.batch_id,
            "region": self.region_code
        }
        url = "/api/batches/"
        content_type = "application/json"
        c = Client()
        return c.post(url, batch_photo_data, content_type=content_type)