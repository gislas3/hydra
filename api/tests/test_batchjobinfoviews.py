import uuid
import datetime as dt
from unittest.mock import patch

from django.test import TestCase
from api.models import Job_Definition, Job_Spec, Batch_Job, Batch, Region

# Test Cases:

# 1. Test that invalid batch_id fails
# 2. Test that batch_id not in db returns nothing
# 3. Test that queued works
# 4. Test that active works
# 5. Test that failed works
# 6. Test that successful works
# 7. Test that total queued works



class TestBatchJobView(TestCase):

    @patch('api.models.models.base.post_save')
    def setUp(self, post_save_mock):
        super().setUp()
        self.job_definition1 = Job_Definition.objects.create(
            name='leprechaun', description='determined to find the gold')
        self.job_spec1 = Job_Spec.objects.create(job_definition=self.job_definition1, run_environment=Job_Spec.AMAZON,
                                                container_image='rainbow-finder', active=True, namespace='The Ireland of yore',
                                                time_limit=dt.timedelta(hours=3), data_threshold=1, created_by=Job_Spec.GREG)
        self.job_definition2 = Job_Definition.objects.create(name="robot", description="robotic")
        self.job_spec2 = Job_Spec.objects.create(job_definition=self.job_definition2, run_environment=Job_Spec.AZURE,
                                                container_image='bee-boo-bop-bop', active=True, namespace='Gears and Wheels',
                                                time_limit=dt.timedelta(hours=3), data_threshold=1, created_by=Job_Spec.KEVIN)
        self.job_spec3 = Job_Spec.objects.create(job_definition=self.job_definition2, run_environment=Job_Spec.AZURE,
                                                container_image='flashy-flashy-spinny-spinny', active=False, namespace='Lights and Music',
                                                time_limit=dt.timedelta(hours=3), data_threshold=1, created_by=Job_Spec.ANDERS)
        self.region = Region.objects.create(code='Crackerbox Palace',
                                            description="we've been expecting yoooooooooou", namespace='George')
        self.batch1 = Batch.objects.create(batch_id=uuid.uuid4(), region=self.region)
        self.batch2 = Batch.objects.create(batch_id=uuid.uuid4(), region=self.region)
        self.batch3 = Batch.objects.create(batch_id=uuid.uuid4(), region=self.region)

        # batch1 - active, queued, failed
        # batch2 - successful, active, failed
        # batch3 - successful, active, queued, also queued with job_spec3
        self.batch1_active_job = Batch_Job.objects.create(job_spec = self.job_spec1, 
            scheduled=True, time_started=dt.datetime.now().replace(tzinfo=dt.timezone.utc))
        self.batch1_active_job.batches.add(self.batch1)
        self.batch1_active_job.save()
        self.batch1_queued_job = Batch_Job.objects.create(job_spec = self.job_spec2)
        self.batch1_queued_job.batches.add(self.batch1)
        self.batch1_queued_job.save()
        self.batch1_failed_job = Batch_Job.objects.create(job_spec = self.job_spec1, 
            scheduled=True, finished=True, time_started=dt.datetime.now().replace(tzinfo=dt.timezone.utc))
        self.batch1_failed_job.batches.add(self.batch1)
        self.batch1_failed_job.save()
        
        self.batch_2_succ_job = Batch_Job.objects.create(job_spec = self.job_spec1, 
            scheduled=True, succeeded=True, time_started=dt.datetime.now().replace(tzinfo=dt.timezone.utc))
        self.batch_2_succ_job.batches.add(self.batch2)
        self.batch_2_succ_job.save()
        self.batch_2_active_job = Batch_Job.objects.create(job_spec = self.job_spec2, 
            scheduled=True, time_started=dt.datetime.now().replace(tzinfo=dt.timezone.utc))
        self.batch_2_active_job.batches.add(self.batch2)
        self.batch_2_active_job.save()

        self.batch_2_failed_job = Batch_Job.objects.create(job_spec = self.job_spec1, 
            scheduled=True, finished=True, time_started=dt.datetime.now().replace(tzinfo=dt.timezone.utc))
        self.batch_2_failed_job.batches.add(self.batch2)
        self.batch_2_failed_job.save()

        self.batch_3_succjob = Batch_Job.objects.create(job_spec = self.job_spec2, 
            scheduled=True, succeeded=True, time_started=dt.datetime.now().replace(tzinfo=dt.timezone.utc))
        self.batch_3_succjob.batches.add(self.batch3)
        self.batch_3_succjob.save()

        self.batch_3_activejob = Batch_Job.objects.create(job_spec = self.job_spec1, 
            scheduled=True,  time_started=dt.datetime.now().replace(tzinfo=dt.timezone.utc))
        self.batch_3_activejob.batches.add(self.batch3)
        self.batch_3_activejob.save()

        self.batch_3_qjob1 = Batch_Job.objects.create(job_spec = self.job_spec1)
        self.batch_3_qjob1.batches.add(self.batch3)
        self.batch_3_qjob1.save()

        self.batch_3_qjob2 = Batch_Job.objects.create(job_spec = self.job_spec3)
        self.batch_3_qjob2.batches.add(self.batch3)
        self.batch_3_qjob2.save()
    
    @patch('api.models.models.base.post_save')
    def test_batch_id_not_in_db_fails(self, post_save_mock):
        resp = self.client.get('/api/jobs-by-batch/', data={"batch_id": "{0}".format(uuid.uuid4())})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {"Message": "Batch doesn't exist"})
    
    @patch('api.models.models.base.post_save')
    def test_invalid_batch_id_fails(self, post_save_mock):
        resp = self.client.get('/api/jobs-by-batch/', data={"batch_id": "UGABOOGA"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {"Message": "Invalid batch_id requested"})

    @patch('api.models.models.base.post_save')
    def test_queued_response_correct(self, post_save_mock):
        resp = self.client.get('/api/jobs-by-batch/', data={"batch_id": str(self.batch1.batch_id)})
        self.assertEqual(resp.status_code, 200)
        data_dict = resp.json()
        self.assertEqual(data_dict["Total_Jobs"], 3)
        self.assertEqual(data_dict["Successful_Jobs"]["Total"], 0)
        self.assertEqual(data_dict['Queued_Jobs']['Total'], 1)
        self.assertEqual(data_dict['Queued_Jobs']['Job_List'][0]["job_name"], self.batch1_queued_job.job_spec.job_definition.name)
    
    @patch('api.models.models.base.post_save')
    def test_active_response_correct(self, post_save_mock):
        resp = self.client.get('/api/jobs-by-batch/', data={"batch_id": str(self.batch2.batch_id)})
        self.assertEqual(resp.status_code, 200)
        data_dict = resp.json()
        self.assertEqual(data_dict["Total_Jobs"], 3)
        self.assertEqual(data_dict["Queued_Jobs"]["Total"], 0)

        self.assertEqual(data_dict['Active_Jobs']['Total'], 1)
        self.assertEqual(data_dict['Active_Jobs']['Job_List'][0]["job_name"], self.batch_2_active_job.job_spec.job_definition.name)
    
    @patch('api.models.models.base.post_save')
    def test_failed_response_correct(self, post_save_mock):
        resp = self.client.get('/api/jobs-by-batch/', data={"batch_id": str(self.batch1.batch_id)})
        self.assertEqual(resp.status_code, 200)
        data_dict = resp.json()
        self.assertEqual(data_dict["Total_Jobs"], 3)

        self.assertEqual(data_dict['Failed_Jobs']['Total'], 1)
        self.assertEqual(data_dict['Failed_Jobs']['Job_List'][0]["job_name"], self.batch1_failed_job.job_spec.job_definition.name)
        self.assertEqual(data_dict['Failed_Jobs']['Job_List'][0]["time_started"], self.batch1_failed_job.time_started.strftime("%Y-%m-%d %H:%M:%S"))

    @patch('api.models.models.base.post_save')
    def test_successful_response_correct(self, post_save_mock):
        resp = self.client.get('/api/jobs-by-batch/', data={"batch_id": str(self.batch3.batch_id)})
        self.assertEqual(resp.status_code, 200)
        data_dict = resp.json()
        self.assertEqual(data_dict["Total_Jobs"], 4)

        self.assertEqual(data_dict['Successful_Jobs']['Total'], 1)
        self.assertEqual(data_dict['Successful_Jobs']['Job_List'][0]["job_name"], self.batch_3_succjob.job_spec.job_definition.name)
        self.assertEqual(data_dict['Successful_Jobs']['Job_List'][0]["time_started"], self.batch_3_succjob.time_started.strftime("%Y-%m-%d %H:%M:%S"))

    @patch('api.models.models.base.post_save')
    def test_total_queued_works(self, post_save_mock):
        resp = self.client.get("/api/jobs-queued/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"Total Queued Jobs": 2} )
        

        