import datetime as dt
import uuid
from unittest.mock import patch

from api.tests.generictestview import GenericTestView
from api.models import Job_Definition, Job_Spec, Batch_Job, Batch, Region


@patch('api.models.models.base.post_save')
class TestBatchJobView(GenericTestView):

    def setUp(self):
        self.job_definition = Job_Definition.objects.create(
            name='leprechaun', description='determined to find the gold')
        self.job_spec = Job_Spec.objects.create(job_definition=self.job_definition, run_environment=Job_Spec.AMAZON,
                                                container_image='rainbow-finder', active=False, namespace='The Ireland of yore',
                                                time_limit=dt.timedelta(hours=3), data_threshold=1, created_by=Job_Spec.GREG)
        self.region = Region.objects.create(code='Crackerbox Palace',
                                            description="we've been expecting yoooooooooou", namespace='George')

    def test_batchjob_get_empty(self, post_save_mock):
        self.generic_get_nothing('batchjobs-list')

    def test_batchjob_get_one(self, post_save_mock):
        Batch_Job.objects.create(job_spec=self.job_spec)
        resp = self.generic_get_one_item('batchjobs-list')
        self.assertIn('1', resp.content.decode())

    def test_batch_job_get_multi(self, post_save_mock):
        Batch_Job.objects.create(job_spec=self.job_spec)
        Batch_Job.objects.create(job_spec=self.job_spec, started=True)
        resp = self.generic_get_one_item('batchjobs-list')
        self.assertIn('1', resp.content.decode())
        self.assertIn('true', resp.content.decode())

    def test_batch_job_get_multi_w_batches(self, post_save_mock):
        bj1 = Batch_Job.objects.create(job_spec=self.job_spec)
        bj2 = Batch_Job.objects.create(job_spec=self.job_spec, started=True)
        batch_id1 = uuid.uuid4()
        batch_id2 = uuid.uuid4()
        batch1 = Batch.objects.create(batch_id=batch_id1, region=self.region)
        batch2 = Batch.objects.create(batch_id=batch_id2, region=self.region)
        bj1.batches.add(batch1)
        bj1.batches.add(batch2)
        bj1.save()
        resp = self.generic_get_one_item('batchjobs-list')
        self.assertIn('1', resp.content.decode())
        self.assertIn('true', resp.content.decode())
        self.assertIn(str(batch_id1), resp.content.decode())
        self.assertIn(str(batch_id2), resp.content.decode())
