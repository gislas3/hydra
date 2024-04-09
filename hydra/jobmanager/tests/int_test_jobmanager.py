import datetime as dt
import time
import logging
import uuid

from unittest import skip
from unittest.mock import patch

from django.test import TestCase
from django.conf import settings

from api.models import Region
from api.models import Batch
from api.models import Job_Definition
from api.models import Job_Spec
from api.models import Batch_Job

from hydra.jobscheduler.jobscheduler import JobScheduler
from hydra.jobmanager.jobmanager import JobManager
import random
import string




class JobManagerIntegrationTestCases(TestCase):
    """
    Test cases for JobManager and subclasses. Most assume that all functions
    in the signals.py file are working appropriately and will be called on
    saving of `Batch_Photo` and `Batch_Job`.
    """
    job_id = 100
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logging.debug("Setup class called")
        cls.device1 = uuid.uuid4()
        test_imu_jd = Job_Definition.objects.create(
            name="test-imu-jobmanager",
            description="testjobmanager",
            parent_job=None
        )
        test_imu_jd_child1 = Job_Definition.objects.create(
            name='test-imu-child1',
            description='testjobmanager',
            parent_job=test_imu_jd
        )
        Job_Definition.objects.create(
            name='test-imu-child2',
            description='testjobmanager',
            parent_job=test_imu_jd_child1
        )
        test_photo_jd2 = Job_Definition.objects.create(
            name="test-photo-jobmanager2",
            description="testjobmanager",
            parent_job=None
        )
        test_child_photo_jd1 = Job_Definition.objects.create(
            name='test-child-photo1',
            description='testjobmanager',
            parent_job=test_photo_jd2
        )
        Job_Definition.objects.create(
            name='test-child-photo2',
            description='testjobmanager',
            parent_job=test_child_photo_jd1
        )
        Job_Spec.objects.create(
            job_definition=test_imu_jd,
            run_environment='k8s',
            container_image=settings.PROCESS_BATCH_TEST_IMAGE,
            time_limit=dt.timedelta(hours=1),
            data_threshold=4,
            namespace='processing-test',
            trigger_children=False,
            k8s_job_labels={"created-for-test": "true"}
        )
        Job_Spec.objects.create(
            job_definition=test_photo_jd2,
            run_environment='k8s',
            container_image=settings.PROCESS_BATCH_TEST_IMAGE,
            time_limit=dt.timedelta(hours=1),
            data_threshold=3,
            namespace='processing-test',
            trigger_children=False,
            k8s_job_labels={"created-for-test": "true"},
            whitelisted_devices=[str(cls.device1)]
        )

    
    def setUp(self):
        logging.debug("setup called, job id is {0}".format(self.job_id))
        self.region = Region.objects.create(
            description="test region", namespace='processing-test')
        # self.batch_id = uuid.uuid4()# Batch.objects.create(region=self.region)
        # Don't like this, but for some reason job_id was always 100 going into this method
        self.job_dict = {}
        JobManagerIntegrationTestCases.job_id += 50 # Should be okay as long as fewer than 100 jobs were created in the previous test method... 
        # jobscheduler.kube_cleanup_finished_jobs(jobs_label_selector="created-for-test=true", namespace="processing-test")


    @classmethod
    def tearDownClass(cls):
        time.sleep(10)
        jobscheduler = JobScheduler()
        jobscheduler.kube_cleanup_jobs_with_state(
            jobs_label_selector="created-for-test=true",
            state="Finished"
        )
        super().tearDownClass()
    
    def mock_make_kubernetes_job_name(self, batch_job):
        logging.debug("In mock make job name, jobid is {0}".format(self.job_id))
        random = uuid.uuid4().hex[:5]
        if batch_job.id in self.job_dict:
            to_ret = "{0}-{1}-{2}".format(batch_job.job_spec.job_definition.name, random, self.job_id)
        else:
            self.job_dict[batch_job.id] = self.job_id
            to_ret = "{0}-{1}-{2}".format(batch_job.job_spec.job_definition.name, random, self.job_id)
            self.job_id += 1
        return to_ret

    # @skip("Causes duplicated k8s job names")
    # def test_run_job_on_cluster(self):
    #     with patch('hydra.jobmanager.jobmanager.JobManager.make_kubernetes_job_name', new=self.mock_make_kubernetes_job_name):

    #         self.assertEquals(Batch_Job.objects.all().count(), 0)
    #         Batch_Photo.objects.create(
    #             batch=self.batch,
    #         )
    #         Batch_Photo.objects.create(
    #             batch=self.batch,
    #         )
    #         self.assertTrue(Batch_Job.objects.all()[0].started)
    #         self.assertEquals(Batch_Job.objects.all().count(), 1)

    
    def test_add_batch_creates_batch_jobs(self):
        with patch('hydra.jobmanager.jobmanager.JobManager.make_kubernetes_job_name', new=self.mock_make_kubernetes_job_name):
            batch_id = uuid.uuid4()
            Batch.objects.create(
                batch_id=batch_id,
                region=self.region
            )
            num_bjobs = Batch_Job.objects.count()
            b_job = Batch_Job.objects.all()[0]
            self.assertEqual(num_bjobs, 2)
            self.assertEqual(b_job.batches.count(), 1)


    def test_add_batch_multi(self):
        with patch('hydra.jobmanager.jobmanager.JobManager.make_kubernetes_job_name', new=self.mock_make_kubernetes_job_name):
            batch_id1 = uuid.uuid4()
            batch_id2 = uuid.uuid4()
            Batch.objects.create(
                batch_id=batch_id1,
                region=self.region
            )
            Batch.objects.create(
                batch_id=batch_id2,
                region=self.region
            )
            b_job = Batch_Job.objects.all()[0]
            b_job2 = Batch_Job.objects.all()[1]
            num_bjobs = Batch_Job.objects.count()
            self.assertEqual(b_job.batches.count(), 2)
            self.assertEqual(b_job2.batches.count(), 2)
            self.assertEqual(num_bjobs, 2)

    def test_add_batches_and_start_one_job(self):
        with patch('hydra.jobmanager.jobmanager.JobManager.make_kubernetes_job_name', new=self.mock_make_kubernetes_job_name):
                Batch.objects.create(
                    batch_id=uuid.uuid4(),
                    region=self.region
                )
                Batch.objects.create(
                    batch_id=uuid.uuid4(),
                    region=self.region
                )
                Batch.objects.create(
                    batch_id=uuid.uuid4(),
                    region=self.region
                )
                Batch.objects.create(
                    batch_id=uuid.uuid4(),
                    region=self.region
                )
                b_job = Batch_Job.objects.filter(job_spec__data_threshold=3)[0]
                job_def_name = b_job.job_spec.job_definition.name
                self.assertTrue(b_job.scheduled)

    def test_add_batches_and_no_start_because_whitelisted_devices(self):
        with patch('hydra.jobmanager.jobmanager.JobManager.make_kubernetes_job_name', new=self.mock_make_kubernetes_job_name):
                Batch.objects.create(
                    batch_id=uuid.uuid4(),
                    device_id=uuid.uuid4(),
                    region=self.region
                )
                Batch.objects.create(
                    batch_id=uuid.uuid4(),
                    device_id=uuid.uuid4(),
                    region=self.region
                )
                Batch.objects.create(
                    batch_id=uuid.uuid4(),
                    device_id=uuid.uuid4(),
                    region=self.region
                )
                Batch.objects.create(
                    batch_id=uuid.uuid4(),
                    device_id=uuid.uuid4(),
                    region=self.region
                )
                self.assertFalse(Batch_Job.objects.filter(job_spec__data_threshold=3).exists())
                self.assertTrue(Batch_Job.objects.filter(job_spec__data_threshold=4).exists())
                self.assertTrue(Batch_Job.objects.filter(job_spec__data_threshold=4).first().scheduled)

                # job_def_name = b_job.job_spec.job_definition.name
                #  self.assertTrue(b_job.scheduled)

    def test_add_batches_and_start_because_whitelisted_devices(self):
        with patch('hydra.jobmanager.jobmanager.JobManager.make_kubernetes_job_name', new=self.mock_make_kubernetes_job_name):
                Batch.objects.create(
                    batch_id=uuid.uuid4(),
                    device_id=self.device1,
                    region=self.region
                )
                Batch.objects.create(
                    batch_id=uuid.uuid4(),
                    device_id=self.device1,
                    region=self.region
                )
                Batch.objects.create(
                    batch_id=uuid.uuid4(),
                    device_id=self.device1,
                    region=self.region
                )
                Batch.objects.create(
                    batch_id=uuid.uuid4(),
                    device_id=self.device1,
                    region=self.region
                )
                self.assertTrue(Batch_Job.objects.filter(job_spec__data_threshold=3).exists())
                self.assertTrue(Batch_Job.objects.filter(job_spec__data_threshold=3).count(), 2)
                self.assertEqual(Batch_Job.objects.filter(job_spec__data_threshold=3, scheduled=True).count(), 1)

                self.assertTrue(Batch_Job.objects.filter(job_spec__data_threshold=4).exists())
                self.assertTrue(Batch_Job.objects.filter(job_spec__data_threshold=4).first().scheduled)

                # job_def_name = b_job.job_spec.job_definition.name
                #  self.assertTrue(b_job.scheduled)

    def test_add_batches_and_no_start_job(self):
        with patch('hydra.jobmanager.jobmanager.JobManager.make_kubernetes_job_name', new=self.mock_make_kubernetes_job_name):

            Batch.objects.create(
                batch_id=uuid.uuid4(),
                region=self.region
            )
            Batch.objects.create(
                batch_id=uuid.uuid4(),
                region=self.region
            )
            b_job = Batch_Job.objects.filter(job_spec__data_threshold=3)
            b_job2 = Batch_Job.objects.filter(job_spec__data_threshold=4)
            self.assertFalse(b_job[0].scheduled)
            self.assertFalse(b_job2[0].started)

    def test_add_batch_and_start_then_no_start(self):
        with patch('hydra.jobmanager.jobmanager.JobManager.make_kubernetes_job_name', new=self.mock_make_kubernetes_job_name):
            for _ in range(0, 4):
                Batch.objects.create(
                batch_id=uuid.uuid4(),
                region=self.region
            )

            num_scheduled = Batch_Job.objects.filter(scheduled=True).count()
            num_not_started = Batch_Job.objects.filter(started=False).count()
            self.assertEqual(num_scheduled, 2)
            self.assertEqual(num_not_started, 3)
            #batch_jobs = Batch_Job.objects.count()
            #self.assertEqual(batch_jobs,3)

    def test_add_batch_and_start_then_start(self):
        with patch('hydra.jobmanager.jobmanager.JobManager.make_kubernetes_job_name', new=self.mock_make_kubernetes_job_name):

            for _ in range(0, 6):
                Batch.objects.create(
                batch_id=uuid.uuid4(),
                region=self.region
            )

            num_scheduled = Batch_Job.objects.filter(scheduled=True).count()
            num_not_started = Batch_Job.objects.filter(started=False).count()
            self.assertEqual(num_scheduled, 3)
            self.assertEqual(num_not_started, 4)


    # TODO: Possibly uncomment depending upon how child jobs will be triggered.
    # def set_up_imu_parents(self):
    #     """
    #     Sets up dependencies for testing of child job behavior.
    #     """
    #     Job_Spec.objects.get(pk=self.imu_job_spec1.id).delete()
    #     parent_spec = Job_Spec.objects.create(
    #         job_definition=self.test_imu_jd,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         data_threshold=3,
    #         namespace='processing',
    #         trigger_children=True
    #     )
    #     child1_spec = Job_Spec.objects.create(
    #         job_definition=self.test_imu_jd_child1,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=3, namespace='processing',
    #         trigger_children=True,
    #     )
    #     child2_spec = Job_Spec.objects.create(
    #         job_definition=self.test_imu_jd_child1,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=3,
    #         namespace='processing',
    #         trigger_children=False,
    #     )
    #     child3_spec = Job_Spec.objects.create(
    #         job_definition=self.test_imu_jd_child2,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=3,
    #         namespace='processing',
    #         trigger_children=False
    #     )
    #     # return parent_spec, child1_spec, child2_spec, child3_spec
    #
    # def set_up_imu_parents2(self):
    #     """
    #     Sets up dependencies of testing of child job behavior.
    #     """
    #     Job_Spec.objects.get(pk=self.imu_job_spec1.id).delete()
    #     parent_spec = Job_Spec.objects.create(
    #         job_definition=self.test_imu_jd,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=3,
    #         namespace='processing',
    #         trigger_children=False
    #     )
    #     child1_spec = Job_Spec.objects.create(
    #         job_definition=self.test_imu_jd_child1,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=3,
    #         namespace='processing',
    #         trigger_children=True
    #     )
    #     child2_spec = Job_Spec.objects.create(
    #         job_definition=self.test_imu_jd_child1,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=3,
    #         namespace='processing',
    #         trigger_children=False,
    #     )
    #     child3_spec = Job_Spec.objects.create(
    #         job_definition=self.test_imu_jd_child2,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=3,
    #         namespace='processing',
    #         trigger_children=False
    #     )
    #
    # def set_up_photo_parents(self):
    #     Job_Spec.objects.get(pk=self.photo_job_spec2.id).delete()
    #     parent_spec = Job_Spec.objects.create(
    #         job_definition=self.test_photo_jd2,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=10,
    #         namespace='processing',
    #         trigger_children=True
    #     )
    #     child1_spec = Job_Spec.objects.create(
    #         job_definition=self.test_child_photo_jd1,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=10,
    #         namespace='processing',
    #         trigger_children=True
    #     )
    #     child2_spec = Job_Spec.objects.create(
    #         job_definition=self.test_child_photo_jd1,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=10,
    #         namespace='processing',
    #         trigger_children=False
    #     )
    #     child3_spec = Job_Spec.objects.create(
    #         job_definition=self.test_child_photo_jd2,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=10,
    #         namespace='processing',
    #         trigger_children=False
    #     )
    #
    # def set_up_photo_parents2(self):
    #     Job_Spec.objects.get(pk=self.photo_job_spec2.id).delete()
    #     parent_spec = Job_Spec.objects.create(
    #         job_definition=self.test_photo_jd2,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=10,
    #         namespace='processing',
    #         trigger_children=False
    #     )
    #     child1_spec = Job_Spec.objects.create(
    #         job_definition=self.test_child_photo_jd1,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=10,
    #         namespace='processing',
    #         trigger_children=True
    #     )
    #     child2_spec = Job_Spec.objects.create(
    #         job_definition=self.test_child_photo_jd2,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=10,
    #         namespace='processing',
    #         trigger_children=False
    #     )
    #     child3_spec = Job_Spec.objects.create(
    #         job_definition=self.test_child_photo_jd2,
    #         run_environment='k8s',
    #         container_image=settings.PROCESS_BATCH_TEST_IMAGE,
    #         time_limit=dt.timedelta(hours=1),
    #         data_threshold=10,
    #         namespace='processing',
    #         trigger_children=False
    #     )
    #
    # def test_imu_child_job_starts(self):
    #     self.set_up_imu_parents()
    #     batch_imu = Batch_IMU.objects.create(
    #         batch=self.batch,
    #         data_version=0,
    #     )
    #     batch_imu = Batch_IMU.objects.create(
    #         batch=self.batch,
    #         data_version=0,
    #     )
    #     batch_imu = Batch_IMU.objects.create(
    #         batch=self.batch,
    #         data_version=0,
    #     )
    #     num_jobs = Batch_Job.objects.all().count()
    #     self.assertEqual(num_jobs, 1)  # 1 job should start here
    #     for bj in Batch_Job.objects.all():
    #         logging.debug("{0}".format(bj.job_spec.job_definition.name))
    #     # Give jobs time to finish
    #     time.sleep(5)
    #     batch_imu = Batch_IMU.objects.create(
    #         batch=self.batch,
    #         data_version=0,
    #     )
    #     # This above line should trigger saving of the batch jobs as
    #     # finished/succeeded, which should trigger child jobs
    #     num_jobs = Batch_Job.objects.all().count()
    #     for bj in Batch_Job.objects.all():
    #         logging.debug("{0}".format(bj.job_spec.job_definition.name))
    #
    #     # Should be: original job, new job, and 2 children jobs
    #     self.assertEqual(num_jobs, 4)
    #     time.sleep(8)  # Wait for 2 child jobs to finish...
    #     batch_imu = Batch_IMU.objects.create(
    #         batch=self.batch,
    #         data_version=0,
    #     )
    #     # Add one more job - this should trigger the last child job to start
    #     num_jobs = Batch_Job.objects.all().count()
    #     for bj in Batch_Job.objects.all():
    #         logging.debug("{0}".format(bj.job_spec.job_definition.name))
    #     self.assertEqual(num_jobs, 5)
    #
    # def test_imu_no_child_job_starts(self):
    #     self.set_up_imu_parents2()
    #     batch_imu = Batch_IMU.objects.create(
    #         batch=self.batch,
    #         data_version=0,
    #     )
    #     batch_imu = Batch_IMU.objects.create(
    #         batch=self.batch,
    #         data_version=0,
    #     )
    #     batch_imu = Batch_IMU.objects.create(
    #         batch=self.batch,
    #         data_version=0,
    #     )
    #     num_jobs = Batch_Job.objects.all().count()
    #     self.assertEqual(num_jobs, 1)  # 1 job should start here
    #     for bj in Batch_Job.objects.all():
    #         logging.debug("{0}".format(bj.job_spec.job_definition.name))
    #     # Give jobs time to finish
    #     time.sleep(5)
    #     batch_imu = Batch_IMU.objects.create(
    #         batch=self.batch,
    #         data_version=0,
    #     )
    #     # This above line should trigger saving of the batch jobs as
    #     # finished/succeeded, which should trigger child jobs
    #     num_jobs = Batch_Job.objects.all().count()
    #     for bj in Batch_Job.objects.all():
    #         logging.debug("{0}".format(bj.job_spec.job_definition.name))
    #
    #     # Should be: original job, new job, and 2 children jobs
    #     self.assertEqual(num_jobs, 2)
    #     time.sleep(8)  # Wait for 2 child jobs to finish...
    #     batch_imu = Batch_IMU.objects.create(
    #         batch=self.batch,
    #         data_version=0,
    #     )
    #     # Add one more job - this should trigger the last child job to start
    #     num_jobs = Batch_Job.objects.all().count()
    #     for bj in Batch_Job.objects.all():
    #         logging.debug("{0}".format(bj.job_spec.job_definition.name))
    #     self.assertEqual(num_jobs, 2)
    #
    # def test_photo_child_job_starts(self):
    #     self.set_up_photo_parents()
    #     batch_photo = Batch_Photo.objects.create(
    #         batch=self.batch,
    #     )
    #     num_jobs = Batch_Job.objects.all().count()
    #     self.assertEqual(num_jobs, 1)  # 1 job should start here
    #     for bj in Batch_Job.objects.all():
    #         logging.debug("{0}".format(bj.job_spec.job_definition.name))
    #     # Give jobs time to finish
    #     time.sleep(8)
    #     batch_photo = Batch_Photo.objects.create(
    #         batch=self.batch,
    #     )
    #     # This above line should trigger saving of the batch jobs as
    #     # finished/succeeded, which should trigger child jobs
    #     num_jobs = Batch_Job.objects.all().count()
    #     for bj in Batch_Job.objects.all():
    #         logging.debug("{0}".format(bj.job_spec.job_definition.name))
    #
    #     # Should be: original job, new job, and 2 children jobs
    #     self.assertEqual(num_jobs, 4)
    #     time.sleep(8)  # Wait for 2 child jobs to finish...
    #     batch_photo = Batch_Photo.objects.create(
    #         batch=self.batch,
    #     )
    #     # Add one more job - this should trigger the last child job to start
    #     time.sleep(2)
    #     num_jobs = Batch_Job.objects.all().count()
    #     for bj in Batch_Job.objects.all():
    #         logging.debug("{0}".format(bj.job_spec.job_definition.name))
    #     self.assertEqual(num_jobs, 5)
    #
    # def test_photo_no_child_job_starts(self):
    #     self.set_up_photo_parents2()
    #     batch_photo = Batch_Photo.objects.create(
    #         batch=self.batch,
    #     )
    #     num_jobs = Batch_Job.objects.all().count()
    #     self.assertEqual(num_jobs, 1)  # 1 job should start here
    #     for bj in Batch_Job.objects.all():
    #         logging.debug("{0}".format(bj.job_spec.job_definition.name))
    #     # Give jobs time to finish
    #     batch_photo = Batch_Photo.objects.create(
    #         batch=self.batch,
    #     )
    #     time.sleep(5)
    #     # This above line should trigger saving of the batch jobs as
    #     # finished/succeeded, which should trigger child jobs
    #     num_jobs = Batch_Job.objects.all().count()
    #     for bj in Batch_Job.objects.all():
    #         logging.debug("{0}".format(bj.job_spec.job_definition.name))
    #
    #     self.assertEqual(num_jobs, 2) # Should be: original job, new job
