import json
import logging
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from api.models import Batch


@patch('api.models.models.base.post_save')
class TestSignal(TestCase):
    def setUp(self):
        self.api_client = APIClient()
        self.batch_id = "4ece9443-35dd-4570-9929-d7d050242134"
        self.region_code = "EU.CARDIFF"  # Not sure what this should be set to
        self.data_version = 2

        # setup Region
        self.setup_region()

    def test_upload_batch_imu_trigger_single_signal(self, patch_mock_ps):
        batch_data = self.generate_hydra_data_body(
            self.batch_id,
            self.region_code
        )
        url = "/api/batches/"
        content_type = "application/json"
        good_response = self.api_client.post(
            url,
            json.dumps(batch_data),
            content_type=content_type,
        )
        if good_response.status_code == 400:
            logging.info(good_response)
        self.assertEqual(good_response.status_code, 201)
        self.assertEqual(len(patch_mock_ps.mock_calls), 1)
        logging.info(patch_mock_ps)

    def test_upload_batch_should_not_trigger(self, patch_mock_ps):
        invalid_batch_data = {"batch": 'Ugabooga',
                              'region_code': 'Outer space'
                              }
        url = "/api/batches/"
        content_type = "application/json"
        good_response = self.api_client.post(
            url,
            json.dumps(invalid_batch_data),
            content_type=content_type,
        )
        logging.info(good_response.status_code)
        self.assertEqual(good_response.status_code, 400)
        self.assertEqual(len(patch_mock_ps.mock_calls), 0)

    def generate_hydra_data_body(
        self,
        batch_id: str,
        region_code: str
    ):
        return {'batch_id': batch_id, 'region': region_code}

    def setup_region(self):
        url = "/api/regions/"
        # url = reverse('regions-list')
        valid_data = {"code": "EU.CARDIFF",
                      "description": "CARDIFF", "namespace": "county"}
        res = self.api_client.post(url, valid_data)
        logging.debug(res)
