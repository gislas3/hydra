import time
import random
import string

#from unittest import TestCase, skip
from django.test import TestCase, TransactionTestCase
from unittest.mock import patch
from unittest import skip
from hydra.jobscheduler.jobscheduler import JobScheduler

from django.conf import settings


class TestJobScheduler(TransactionTestCase):
    def setUp(self):
        self.jobscheduler = JobScheduler()
        self.container_test_image = settings.PROCESS_BATCH_TEST_IMAGE
        self.job_namespace = "processing-test"
        self.job_name_prefix = "hydra-test-k8s-job"
        self.test_batch_id = {"BATCH_IDS":"6083fd66-f76b-45b3-b23a-d114ec0b3c22"}
        self.job_labels = {"created-for-test": "true"}
        self.TIMEOUT = 10 # The time we have to wait for the k8s to actualy perform its task

    def tearDown(self):
        pass

    @classmethod
    def tearDownClass(cls):
        jobscheduler = JobScheduler()
        jobscheduler.kube_cleanup_jobs_with_state(jobs_label_selector="created-for-test=true", state="Finished", namespace="processing-test")
        super().tearDownClass()
        # pass



    def test_create_k8s_job_with_single_batch_should_succeed(self):
        job_name = self.get_job_name()
        job_api_response = self.jobscheduler.kube_create_job(job_name, self.job_namespace, self.test_batch_id, self.container_test_image, labels=self.job_labels)
        V1JobStatus = job_api_response.status
        job_status = V1JobStatus.succeeded
        expected = None
        # As soon as the job is created, the status will be None. Only after the k8s API have created the job will it have a status
        actual = job_status
        assert expected == actual
        time.sleep(self.TIMEOUT + 5) # We need to make sure that the k8s API have created the job
        job_status = self.jobscheduler.kube_get_job_status(job_name, self.job_namespace)
        expected = "succeeded"
        actual = job_status
        self.assertEqual(expected,actual)

    @skip("Causes error in the output, so skipping this")
    def test_create_k8s_job_with_single_batch_should_fail(self):
        job_name = "cannot be created" # whitespace in k8s jobname causes a failure
        job_api_response = self.jobscheduler.kube_create_job(job_name, self.job_namespace, self.test_batch_id, self.container_test_image, labels=self.job_labels)
        expected = "Invalid"
        actual = job_api_response
        self.assertEqual(expected,actual)


    def test_create_k8s_job_with_multiple_batches(self):
        job_env = {
            "BATCH_IDS": "6083fd66-f76b-45b3-b23a-d114ec0b3c22,6083fd66-f76b-45b3-h23a-d114ec0b3c44",
            "SLEEP_TIME" : "1"
            }
        job_name = self.get_job_name()
        job_body = self.jobscheduler.kube_create_job(job_name, self.job_namespace, job_env, self.container_test_image, labels=self.job_labels)
        time.sleep(self.TIMEOUT + 5) # We need to make sure that the k8s API have created the job
        job_status = self.jobscheduler.kube_get_job_status(job_name, self.job_namespace)
        expected = "succeeded"
        actual = job_status
        self.assertEqual(expected,actual)

    def test_create_k8s_job_already_exists_should_fail(self):
        job_env = {
            "BATCH_IDS": "6083fd66-f76b-45b3-b23a-d114ec0b3c22,6083fd66-f76b-45b3-h23a-d114ec0b3c44",
            "SLEEP_TIME" : "1"
            }
        job_name = "hydra-test-duplicate-name-expected-k8s-job"
        k8s_api_response_1 = self.jobscheduler.kube_create_job(job_name, self.job_namespace, job_env, self.container_test_image, labels=self.job_labels)
        k8s_api_response_2 = self.jobscheduler.kube_create_job(job_name, self.job_namespace, job_env, self.container_test_image, labels=self.job_labels)
        expected = "AlreadyExists"
        actual = k8s_api_response_2
        self.assertEqual(expected,actual)

    @skip("Not implemented yet")
    def test_get_output_from_k8s_job(self):
        assert False

    def test_get_status_from_k8s_job(self):
        job_name = "test-k8s-job-get-status" + self.id_generator()
        job_body = self.jobscheduler.kube_create_job(job_name, self.job_namespace, self.test_batch_id, self.container_test_image, labels=self.job_labels)
        time.sleep(2)
        job_status = self.jobscheduler.kube_get_job_status(job_name, self.job_namespace)
        expected = "active"
        actual = job_status
        self.assertEqual(expected, actual)
        time.sleep(self.TIMEOUT) # We have to wait for the job to be started and running
        job_status = self.jobscheduler.kube_get_job_status(job_name, self.job_namespace)
        expected = "succeeded"
        actual = job_status
        self.assertEqual(expected,actual)

    def test_delete_k8s_jobs(self):
        job_labels = self.job_labels
        label = "created-to-test-deletetion"
        job_labels.update({label:"true"})
        job_name = self.get_job_name()
        job_body = self.jobscheduler.kube_create_job(job_name, self.job_namespace, self.test_batch_id, self.container_test_image, labels=job_labels)
        time.sleep(self.TIMEOUT) # wait for job to complete
        deleted_jobs = self.jobscheduler.kube_cleanup_jobs_with_state(jobs_label_selector=label + "=true", namespace=self.job_namespace)
        assert job_name in deleted_jobs

    def test_create_photo_container_with_init_container(self):
        test_batch_id = {}
        container_test_image = "registry.mobilizedconstruction.com/mc/s3-image-client/generate-video:latest"
        job_labels = self.job_labels
        job_env = {
            "AWS_ACCESS_KEY_ID": "vault:secret/data/hydra#AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY": "vault:secret/data/hydra#AWS_SECRET_ACCESS_KEY",
            "BATCH_IDS": "b508b649-7691-4775-936b-91a6c8ac702b"
        }
        init_photo_container = True
        job_labels.update({"created-to-test-deletetion":"true"})
        job_name = self.get_job_name()
        job_body = self.jobscheduler.kube_create_job(job_name, self.job_namespace, job_env, container_test_image, init_photo_container=init_photo_container, labels=job_labels)


        time.sleep(45) # wait for job to complete. Because this is running with a photo init container and downloading image we have to wait a bit longer
        job_status = self.jobscheduler.kube_get_job_status(job_name, self.job_namespace)
        expected = "succeeded"
        actual = job_status
        self.assertEqual(expected,actual)


    def test_create_photo_container_without_init_container_should_fail(self):
        test_batch_id = {"BATCH_IDS":"4b037dd8-0d7d-4892-8bb3-e00009ebaba1"}
        container_test_image = "registry.mobilizedconstruction.com/mc/s3-image-client/generate-video:latest"
        job_labels = self.job_labels
        init_photo_container = False
        job_labels.update({"created-to-test-deletetion":"true"})
        job_name = self.get_job_name()
        job_body = self.jobscheduler.kube_create_job(job_name, self.job_namespace, test_batch_id, container_test_image, init_photo_container, labels=job_labels)
        time.sleep(self.TIMEOUT) # wait for job to complete. Because this is running with a photo init container and downloading image we have to wait a bit longer
        job_status = self.jobscheduler.kube_get_job_status(job_name, self.job_namespace)
        expected = ("failed", "active")
        actual = job_status
        self.assertIn(actual, expected)
        time.sleep(5)
        self.jobscheduler.kube_delete_job(job_name,self.job_namespace)

    def id_generator(self,size=6, chars=string.ascii_lowercase + string.digits):
        return "-"+''.join(random.choice(chars) for _ in range(size))

    def get_job_name(self):
        job_name = self.job_name_prefix + self.id_generator()
        return job_name
