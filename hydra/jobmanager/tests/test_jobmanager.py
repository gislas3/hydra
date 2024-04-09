import datetime as dt
from unittest import skip
from unittest.mock import patch

from django.test import TestCase
from django.conf import settings
from unittest.mock import patch
import os
from hydra.jobmanager.jobmanager import JobManager
from api.models import Batch_Job
from api.models import Job_Spec
from api.models import Job_Definition


@patch('hydra.jobmanager.jobmanager.jobscheduler')
class TestJobManager(TestCase):

    def setUp(self):
        self.test_imu_jd = Job_Definition.objects.create(name="test-imu-jobmanager",
                                                         description="testjobmanager", parent_job=None)
        self.imu_job_spec1 = Job_Spec.objects.create(job_definition=self.test_imu_jd, run_environment='k8s',
                                                     container_image="registry.mobilizedconstruction.com/mc/hydra/process-batch-test:latest",  time_limit=dt.timedelta(hours=1),
                                                     data_threshold=3, namespace='processing-test', trigger_children=False, k8s_job_labels={"created-for-test": "true"})
        self.j_manager = JobManager()

    def test_make_kubernetes_job_name(self, patch_mock_js):
        b_job = Batch_Job(job_spec=self.imu_job_spec1)
        b_job.save()
        self.assertEquals(self.j_manager.make_kubernetes_job_name(b_job), "test-imu-jobmanager-{0}".format(b_job.id))

    def test_on_job_failure(self, patch_mock_js):
        b_job = Batch_Job(job_spec=self.imu_job_spec1)
        self.assertEquals(b_job.tries, 0)
        self.assertFalse(b_job.finished)
        self.j_manager.on_job_failure(b_job, 1)
        b_job.refresh_from_db()
        self.assertEqual(b_job.tries, 1)

    def test_on_job_failure_with_string_job_tries(self, patch_mock_js):
        b_job = Batch_Job(job_spec=self.imu_job_spec1)
        self.assertEquals(b_job.tries, 0)
        self.assertFalse(b_job.finished)
        self.j_manager.on_job_failure(b_job, str(1))
        b_job.refresh_from_db()
        self.assertTrue(isinstance(b_job.tries,int))
        self.assertEqual(b_job.tries, 1)
        self.j_manager.on_job_failure(b_job, str(0))
        b_job.refresh_from_db()
        self.assertTrue(isinstance(b_job.tries,int))
        self.assertEqual(b_job.tries, 0)


    def test_on_job_success(self, patch_mock_js):
        b_job = Batch_Job(job_spec=self.imu_job_spec1)
        self.assertFalse(b_job.succeeded)
        self.assertFalse(b_job.finished)
        self.j_manager.on_job_success(b_job)
        b_job.refresh_from_db()
        self.assertTrue(b_job.succeeded)
        self.assertTrue(b_job.finished)

    def test_on_job_started(self, patch_mock_js):
        b_job = Batch_Job(job_spec=self.imu_job_spec1)
        self.assertFalse(b_job.started)
        start_time = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
        self.j_manager.on_job_started(b_job, start_time)
        b_job.refresh_from_db()
        self.assertFalse(b_job.succeeded)
        self.assertFalse(b_job.finished)
        self.assertTrue(b_job.started)
        self.assertEqual(b_job.tries, 0)

    def test_on_job_created(self, patch_mock_js):
        b_job = Batch_Job(job_spec=self.imu_job_spec1)
        self.assertFalse(b_job.started)
        self.assertFalse(b_job.created_on_k8s)
        self.j_manager.on_job_created(b_job)
        b_job.refresh_from_db()
        self.assertTrue(b_job.created_on_k8s)
        self.assertFalse(b_job.succeeded)
        self.assertFalse(b_job.finished)
        self.assertFalse(b_job.started)
        self.assertEqual(b_job.tries, 0)

    def test_max_active_jobs_from_env(self,patch_mock_js):
        # because jobmanager is a singleton, we need to remove the instance variable (set to None)
        # to create a new JobManager instance for every test
        JobManager._instance = None
        max_active_k8s_jobs = 13
        with self.settings(MAX_ACTIVE_K8S_JOBS=max_active_k8s_jobs):
            self.j_manager = JobManager()
            self.assertEqual(self.j_manager.max_active_jobs, max_active_k8s_jobs)

    def test_max_active_jobs_from_env_as_string(self,patch_mock_js):
        # because jobmanager is a singleton, we need to remove the instance variable (set to None)
        # to create a new JobManager instance for every test
        JobManager._instance = None
        max_active_k8s_jobs = 13
        with self.settings(MAX_ACTIVE_K8S_JOBS=str(max_active_k8s_jobs)):
            self.j_manager = JobManager()
            self.assertTrue(isinstance(settings.MAX_ACTIVE_K8S_JOBS, str))
            self.assertTrue(isinstance(self.j_manager.max_active_jobs, int))
            self.assertEqual(self.j_manager.max_active_jobs, max_active_k8s_jobs)


    def test_max_active_jobs_from_default_if_env_not_set(self,patch_mock_js):
        # because jobmanager is a singleton, we need to remove the instance variable (set to None)
        # to create a new JobManager instance for every test
        JobManager._instance = None
        self.j_manager = JobManager()
        self.assertEqual(self.j_manager.max_active_jobs, settings.MAX_ACTIVE_K8S_JOBS)