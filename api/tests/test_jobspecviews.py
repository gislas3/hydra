import datetime as dt
import json
import uuid
import logging

from api.tests.generictestview import GenericTestView
from api.models import Job_Definition, Job_Spec

# Extra test cases:
# invalid run environment
# invalid job definition
# invalid created by field


class TestJobSpecViews(GenericTestView):

    def setUp(self):
        self.job_definition = Job_Definition.objects.create(
            name='leprechaun', description='determined to find the gold')

    def test_job_spec_get_empty(self):
        self.generic_get_nothing('jobspecs-list')

    def test_job_spec_get_one(self):
        Job_Spec.objects.create(job_definition=self.job_definition, run_environment=Job_Spec.AMAZON,
                                container_image='rainbow-finder', active=False, namespace='The Ireland of yore',
                                time_limit=dt.timedelta(hours=3), data_threshold=1, created_by=Job_Spec.GREG)
        resp = self.generic_get_one_item('jobspecs-list')
        self.assertIn('rainbow-finder', resp.content.decode())

    def test_job_spec_get_multi(self):
        Job_Spec.objects.create(job_definition=self.job_definition, data_threshold=1, run_environment=Job_Spec.AMAZON,
                                container_image='rainbow-finder', active=False, namespace='The Ireland of yore',
                                time_limit=dt.timedelta(hours=3), created_by=Job_Spec.GREG)
        Job_Spec.objects.create(job_definition=self.job_definition, data_threshold=1, run_environment=Job_Spec.AMAZON,
                                container_image='gold-detector', active=False, namespace='The Ireland of yore',
                                time_limit=dt.timedelta(hours=3), created_by=Job_Spec.GREG)
        resp = self.generic_get_multiple_items('jobspecs-list')
        self.assertIn('rainbow-finder', resp.content.decode())
        self.assertIn('gold-detector', resp.content.decode())

    def test_job_spec_post_success(self):
        data = {
            "job_definition": 1,
            "run_environment": 'AWS',
            "container_image": "rainbow-finder",
            "active": True,
            'data_threshold': 1,
            "namespace": 'The Ireland of yore',
            "time_limit": '03:00:00',
            'created_by': 'greg',
            'environment_variables': json.dumps({'shirt-color': 'green', 'hat': 'top'})

        }
        js_count = Job_Spec.objects.all().count()
        self.assertEqual(js_count, 0)
        self.generic_post_success('jobspecs-list', data)
        js_count = Job_Spec.objects.all().count()
        self.assertEqual(js_count, 1)
    
    def test_job_spec_post_success_whitelisted_device(self):
        device1, device2 = uuid.uuid4(), uuid.uuid4()
        data = {
            "job_definition": 1,
            "run_environment": 'AWS',
            "container_image": "rainbow-finder",
            "active": True,
            'data_threshold': 1,
            "namespace": 'The Ireland of yore',
            "time_limit": '03:00:00',
            'created_by': 'greg',
            'environment_variables': json.dumps({'shirt-color': 'green', 'hat': 'top'}),
            'whitelisted_devices': ["{0}".format(device1), "{0}".format(device2)]
        }
        js_count = Job_Spec.objects.all().count()
        self.assertEqual(js_count, 0)
        self.generic_post_success('jobspecs-list', data)
        js_count = Job_Spec.objects.all().count()
        self.assertEqual(js_count, 1)
        js = Job_Spec.objects.first()
        device_set = set(map(lambda x: uuid.UUID(x), js.whitelisted_devices))
        self.assertIn(device1, device_set)
        self.assertIn(device2, device_set)

    def test_job_spec_post_failure_missing_jd(self):
        data = {
            "run_environment": 'AWS',
            "container_image": "rainbow-finder",
            "active": True,
            'data_threshold': 1,
            "namespace": 'The Ireland of yore',
            "time_limit": '03:00:00',
            'created_by': 'greg',
            'environment_variables': json.dumps({'shirt-color': 'green', 'hat': 'top'})

        }
        js_count = Job_Spec.objects.all().count()
        self.assertEqual(js_count, 0)
        self.generic_post_failure('jobspecs-list', data)
        js_count = Job_Spec.objects.all().count()
        self.assertEqual(js_count, 0)

    def test_job_spec_post_failure_invalid_created_by(self):
        data = {
            "job_definition": 1,
            "run_environment": 'AWS',
            "container_image": "rainbow-finder",
            "active": True,
            'data_threshold': 1,
            "namespace": 'The Ireland of yore',
            "time_limit": '03:00:00',
            'created_by': 'patrick',
            'environment_variables': json.dumps({'shirt-color': 'green', 'hat': 'top'})

        }

        js_count = Job_Spec.objects.all().count()
        self.assertEqual(js_count, 0)
        self.generic_post_failure('jobspecs-list', data)
        js_count = Job_Spec.objects.all().count()
        self.assertEqual(js_count, 0)

    def test_job_spec_post_failure_invalid_run_env(self):
        data = {
            "job_definition": 1,
            "run_environment": 'Rainbow road',
            "container_image": "rainbow-finder",
            "active": True,
            'data_threshold': 1,
            "namespace": 'The Ireland of yore',
            "time_limit": '03:00:00',
            'created_by': 'greg',
            'environment_variables': json.dumps({'shirt-color': 'green', 'hat': 'top'})

        }
        js_count = Job_Spec.objects.all().count()
        self.assertEqual(js_count, 0)
        self.generic_post_failure('jobspecs-list', data)
        js_count = Job_Spec.objects.all().count()
        self.assertEqual(js_count, 0)

    def test_job_spec_get_object(self):
        Job_Spec.objects.create(job_definition=self.job_definition, run_environment=Job_Spec.AMAZON,
                                container_image='rainbow-finder', active=False, data_threshold=1, namespace='The Ireland of yore',
                                time_limit=dt.timedelta(hours=3), created_by=Job_Spec.GREG)
        resp = self.generic_get_object_exists('jobspecs-details', [1])
        self.assertIn('rainbow-finder', resp.content.decode())

    def test_job_spec_get_object_fail(self):
        Job_Spec.objects.create(job_definition=self.job_definition, run_environment=Job_Spec.AMAZON,
                                container_image='rainbow-finder', active=False, data_threshold=1, namespace='The Ireland of yore',
                                time_limit=dt.timedelta(hours=3), created_by=Job_Spec.GREG)
        self.generic_get_object_dne('jobspecs-details', [33])

    def test_job_spec_put_object_success(self):
        Job_Spec.objects.create(job_definition=self.job_definition, run_environment=Job_Spec.AMAZON,
                                container_image='rainbow-finder', active=False, data_threshold=1, namespace='The Ireland of yore',
                                time_limit=dt.timedelta(hours=3), created_by=Job_Spec.GREG)
        self.generic_put_success('jobspecs-details', [1], data={'job_definition': 1,
                                                                'run_environment': 'AZ',
                                                                'active': True,
                                                                'container_image': 'rainbow-finder-new-improved',
                                                                'created_by': 'kevin',
                                                                'namespace': 'Northern Ireland of today',
                                                                'time_limit': '03:00:00',
                                                                'data_threshold': 1,
                                                                'environment_variables': json.dumps({'sensor': 'rainbow-detector'})
                                                                }
                                 )
        js = Job_Spec.objects.get(pk=1)
        self.assertEqual(js.container_image, 'rainbow-finder-new-improved')
        self.assertEqual(js.namespace, 'Northern Ireland of today')

    def test_job_spec_put_object_success2(self):
        Job_Spec.objects.create(job_definition=self.job_definition, run_environment=Job_Spec.AMAZON,
                                container_image='rainbow-finder', active=False, data_threshold=1, namespace='The Ireland of yore',
                                time_limit=dt.timedelta(hours=3), created_by=Job_Spec.GREG)
        self.generic_put_success('jobspecs-details', [1],
                                 data={'job_definition': 1,
                                       'run_environment': 'AZ',
                                       'data_threshold': 2,
                                       'container_image': 'rainbow-finder-new-improvedv2',
                                       'created_by': 'kevin',
                                       'namespace': 'Northern Ireland of today',
                                       'time_limit': '03:00:00'
                                       })
        js = Job_Spec.objects.get(pk=1)
        self.assertEqual(js.container_image, 'rainbow-finder-new-improvedv2')
        self.assertEqual(js.environment_variables, {})

    def test_job_spec_put_object_failure_bad_id(self):
        Job_Spec.objects.create(job_definition=self.job_definition, run_environment=Job_Spec.AMAZON,
                                container_image='rainbow-finder', active=False, namespace='The Ireland of yore',
                                time_limit=dt.timedelta(hours=3), data_threshold=1, created_by=Job_Spec.GREG)
        self.generic_put_failure('jobspecs-details', [55], data={'job_definition': 1,
                                                                 'container_image': 'rainbow-finder-new-improvedv2',
                                                                 'run_environment': 'AZ',
                                                                 'created_by': 'kevin',
                                                                 'namespace': 'Northern Ireland of today',
                                                                 'time_limit': '03:00:00',
                                                                 'data_threshold': 2
                                                                 }, expected_code=404)
        js = Job_Spec.objects.get(pk=1)
        self.assertEqual(js.container_image, 'rainbow-finder')
        self.assertEqual(js.namespace, 'The Ireland of yore')

    def test_job_spec_put_object_failure_bad_user(self):
        Job_Spec.objects.create(job_definition=self.job_definition, run_environment=Job_Spec.AMAZON,
                                container_image='rainbow-finder', active=False, namespace='The Ireland of yore',
                                time_limit=dt.timedelta(hours=3), data_threshold=1, created_by=Job_Spec.GREG)
        self.generic_put_failure('jobspecs-details', [1], data={'job_definition': 1,
                                                                'container_image': 'rainbow-finder-new-improvedv2',
                                                                'run_environment': 'AZ',
                                                                'created_by': 'hacker',
                                                                'namespace': 'Northern Ireland of today',
                                                                'time_limit': '03:00:00',
                                                                'data_threshold': 5
                                                                })
        js = Job_Spec.objects.get(pk=1)
        self.assertEqual(js.container_image, 'rainbow-finder')
        self.assertEqual(js.namespace, 'The Ireland of yore')
        self.assertEqual(js.created_by, Job_Spec.GREG)
