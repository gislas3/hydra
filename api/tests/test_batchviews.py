import uuid
import logging
from unittest.mock import patch

# from django.db.models.signals import post_save

from api.tests.generictestview import GenericTestView
from api.models import Batch, Region

def houston_mocker(endpoint, data):
    logging.critical("HOUSTON DATA: {0}".format(data))
# Note: This was really tricky figuring out what to patch, this helped me a lot: https://docs.python.org/3/library/unittest.mock.html#id6
@patch('api.models.models.base.post_save')
class TestBatchViews(GenericTestView):

    def setUp(self):
        self.region = Region.objects.create(code='Crackerbox Palace', 
        description="we've been expecting yoooooooooou", namespace='George')

    

    def test_batch_get_empty(self, post_save_mock):
        self.generic_get_nothing('batches-list')
        self.assertEqual(len(post_save_mock.mock_calls), 0)

    def test_batch_get_one(self, post_save_mock):
        batch_id = uuid.uuid4()
        Batch.objects.create(batch_id=batch_id, region=self.region)
        resp = self.generic_get_one_item('batches-list')
        self.assertIn(str(batch_id), resp.content.decode())
        self.assertEqual(len(post_save_mock.mock_calls), 1)
    
    def test_batch_get_multi(self, post_save_mock):
        batch_id1, batch_id2 = uuid.uuid4(), uuid.uuid4()
        Batch.objects.create(batch_id=batch_id1, region=self.region)
        Batch.objects.create(batch_id=batch_id2, region=self.region)
        resp = self.generic_get_multiple_items('batches-list')
        self.assertIn(str(batch_id1), resp.content.decode())
        self.assertIn(str(batch_id2), resp.content.decode())
        self.assertEqual(len(post_save_mock.mock_calls), 2)

    @patch('api.views._notify_houston')
    def test_batch_post_success(self, notify_houston_mock, post_save_mock):
        batch_id = uuid.uuid4()
        data = {
                "batch_id": str(batch_id),
                "region": self.region.code
            }
        r_count = Region.objects.count()
        self.assertEqual(r_count, 1)
        batch_count = Batch.objects.all().count()
        self.assertEqual(batch_count, 0)
        self.generic_post_success('batches-list', data)
        batch_count = Batch.objects.all().count()
        self.assertEqual(batch_count, 1)
        r_count = Region.objects.count()
        self.assertEqual(r_count, 1)
        self.assertEqual(len(post_save_mock.mock_calls), 1)
        self.assertEqual(len(notify_houston_mock.mock_calls), 2)
    
    @patch('api.views._notify_houston')
    def test_batch_post_failure_bad_region(self, notify_houston_mock, post_save_mock):
        batch_id = uuid.uuid4()
        data = {
                'batch_id': batch_id,
                'region': "Wubbalubbadubdub"
            }
        batch_count = Batch.objects.all().count()
        self.assertEqual(batch_count, 0)
        self.generic_post_failure('batches-list', data)
        batch_count = Batch.objects.all().count()
        self.assertEqual(batch_count, 0)
        self.assertEqual(len(post_save_mock.mock_calls),  0)
        self.assertEqual(len(notify_houston_mock.mock_calls), 0)
    
    @patch('api.views._notify_houston')
    def test_batch_post_failure_bad_batch_id(self, notify_houston_mock, post_save_mock):
        batch_id = "Wubbalubbadubdub"
        data = {
                'batch_id': batch_id,
                'region': self.region.code
            }
        batch_count = Batch.objects.all().count()
        self.assertEqual(batch_count, 0)
        self.generic_post_failure('batches-list', data)
        batch_count = Batch.objects.all().count()
        self.assertEqual(batch_count, 0)
        self.assertEqual(len(post_save_mock.mock_calls),  0)
        self.assertEqual(len(notify_houston_mock.mock_calls), 0)

    @patch('api.views._notify_houston')
    def test_batch_post_success_already_exists(self, notify_houston_mock, post_save_mock):
        batch_id = uuid.uuid4()
        data = {
                'batch_id': batch_id,
                'region': self.region.code
            }
        batch_count = Batch.objects.count()
        self.assertEqual(batch_count, 0)
        self.generic_post_success('batches-list', data)
        batch_count = Batch.objects.count()
        self.assertEqual(batch_count, 1)
        self.generic_post_success('batches-list', data, 200)
        batch_count = Batch.objects.count()
        self.assertEqual(batch_count, 1)
        self.assertEqual(len(post_save_mock.mock_calls), 2)
        self.assertEqual(len(notify_houston_mock.mock_calls), 4)

    @patch('api.views._notify_houston')
    def test_batch_post_device_id(self, notify_houston_mock, post_save_mock):
        batch_id = uuid.uuid4()
        device_id = uuid.uuid4()
        data = {
                'batch_id': batch_id,
                'device_id': device_id,
                'region': self.region.code
            }
        batch_count = Batch.objects.count()
        self.assertEqual(batch_count, 0)
        self.generic_post_success('batches-list', data)
        batch_count = Batch.objects.count()
        self.assertEqual(batch_count, 1)
        self.generic_post_success('batches-list', data, 200)
        batch_count = Batch.objects.count()
        batch = Batch.objects.first()
        self.assertEqual(device_id, batch.device_id)
        self.assertEqual(batch_id, batch.batch_id)
        self.assertEqual(batch_count, 1)
        self.assertEqual(len(post_save_mock.mock_calls), 2)
        self.assertEqual(len(notify_houston_mock.mock_calls), 4)

    def test_batch_get_object(self, post_save_mock):
        batch_id = uuid.uuid4()
        Batch.objects.create(batch_id=batch_id, region=self.region)
        resp = self.generic_get_object_exists('batches-details', [str(batch_id)])
        self.assertIn(str(batch_id), resp.content.decode())
        self.assertEqual(len(post_save_mock.mock_calls), 1)
    
    @patch('api.views._notify_houston', houston_mocker)
    def test_batch_get_object_fail(self,  post_save_mock):
        batch_id = uuid.uuid4()
        Batch.objects.create(batch_id=batch_id, region=self.region)
        self.generic_get_object_dne('batches-details', [str(uuid.uuid4())])
        self.assertEqual(len(post_save_mock.mock_calls),  1)

    @patch('api.views._notify_houston', houston_mocker)
    def test_batch_put_object_success(self, post_save_mock):
        batch_id = uuid.uuid4()
        b = Batch.objects.create(batch_id=batch_id, region=self.region)
        self.assertIsNone(b.updated_at)
        self.generic_put_success('batches-details', [batch_id.hex], data={'batch_id': batch_id})
        b.refresh_from_db()
        self.assertIsNotNone(b.updated_at)
        self.assertEqual(len(post_save_mock.mock_calls),  2)

    @patch('api.views._notify_houston', houston_mocker)
    def test_batch_put_object_success2(self, post_save_mock):
        batch_id = uuid.uuid4()
        b = Batch.objects.create(batch_id=batch_id, region=self.region)
        self.assertIsNone(b.updated_at)
        self.generic_put_success('batches-details', [batch_id.hex], data={'batch_id': batch_id, 'salkfjsdalfk;j': 'klajsfl;asdkjfsad'})
        b.refresh_from_db()
        self.assertIsNotNone(b.updated_at)
        self.assertEqual(b.batch_id, batch_id)
        self.assertEqual(len(post_save_mock.mock_calls),  2)

    @patch('api.views._notify_houston', houston_mocker)
    def test_job_definition_put_object_failure(self, post_save_mock):
        batch_id = uuid.uuid4()
        b = Batch.objects.create(batch_id=batch_id, region=self.region)
        self.assertIsNone(b.updated_at)
        fake_batch_id = uuid.uuid4().hex
        self.generic_put_failure('batches-details', [fake_batch_id], data={'batch_id': fake_batch_id})
        b.refresh_from_db()
        self.assertIsNone(b.updated_at)
        self.assertEqual(len(post_save_mock.mock_calls),  1)

    # def test_batch_put_object_fail(self, post_save_mock):
    #     new_region = Region.objects.create(code='EU.CARDIFF', description='CARDIFF', namespace='Whatever')
    #     batch_id = uuid.uuid4()
    #     Batch.objects.create(batch_id=batch_id, region=self.region)
    #     batch = Batch.objects.get(batch_id=batch_id)
    #     self.assertEqual(batch.region.code, 'Crackerbox Palace')
    #     self.generic_put_faliure('batches-details', [str(batch_id)], data={ 'region': new_region.code}, expected_code=405)
    #     batch = Batch.objects.get(batch_id=batch_id)
    #     self.assertEqual(batch.region.code, 'Crackerbox Palace')
    #     self.assertEqual(len(post_save_mock.mock_calls),  2)
