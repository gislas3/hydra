from api.models import Job_Definition
from api.tests.generictestview import GenericTestView


class TestJobDefinitionViews(GenericTestView):

    def test_job_definition_get_empty(self):
        self.generic_get_nothing('jobs-list')

    def test_job_definition_get_one(self):

        Job_Definition.objects.create(
            name='Handy man', description='Very handy')
        resp = self.generic_get_one_item('jobs-list')
        self.assertIn('Handy man', resp.content.decode())

    def test_job_definition_get_multi(self):
        Job_Definition.objects.create(
            name='Handy man', description='Very handy')
        Job_Definition.objects.create(
            name='Day laborer', description='will not work at night')
        resp = self.generic_get_multiple_items('jobs-list')
        self.assertIn('Handy man', resp.content.decode())
        self.assertIn('Day laborer', resp.content.decode())

    def test_job_definition_post_success(self):
        data = {
            "name": "Museum caretaker",
            "description": "Will care for your museum, but at a price"
        }
        jd_count = Job_Definition.objects.all().count()
        self.assertEqual(jd_count, 0)
        self.generic_post_success('jobs-list', data)
        jd_count = Job_Definition.objects.all().count()
        self.assertEqual(jd_count, 1)

    def test_job_definition_post_failure(self):
        data = {
            "nombre": "pescador",
            "description": "we dont speak spanish and we dont want fish",
        }
        jd_count = Job_Definition.objects.all().count()
        self.assertEqual(jd_count, 0)
        self.generic_post_failure('jobs-list', data)
        jd_count = Job_Definition.objects.all().count()
        self.assertEqual(jd_count, 0)

    def test_job_definition_post_failure_no_name(self):
        data = {
            "description": "what am I supposed to do?!"
        }
        jd_count = Job_Definition.objects.all().count()
        self.assertEqual(jd_count, 0)
        self.generic_post_failure('jobs-list', data)
        jd_count = Job_Definition.objects.all().count()
        self.assertEqual(jd_count, 0)

    def test_job_definition_post_failure_no_name(self):
        data = {
            "description": "we dont speak spanish and we dont want fish",
        }
        jd_count = Job_Definition.objects.all().count()
        self.assertEqual(jd_count, 0)
        self.generic_post_failure('jobs-list', data)
        jd_count = Job_Definition.objects.all().count()
        self.assertEqual(jd_count, 0)

    def test_job_definition_get_object(self):
        Job_Definition.objects.create(
            name='Rolly polly farmer', description='round')
        resp = self.generic_get_object_exists('jobs-details', [1])
        self.assertIn('Rolly polly farmer', resp.content.decode())

    def test_job_definition_get_object_fail(self):
        Job_Definition.objects.create(name='president', description='orange')
        self.generic_get_object_dne('jobs-details', [42])

    def test_job_definition_put_object_success(self):
        Job_Definition.objects.create(
            name='president', description='orange/old')
        self.generic_put_success('jobs-details', [1], data={'name': 'president',
                                                            'description': 'not-orange/older'})
        jd = Job_Definition.objects.get(pk=1)
        self.assertEqual(jd.description, 'not-orange/older')

    def test_job_definition_put_object_success2(self):
        Job_Definition.objects.create(
            name='berry eater', description='black bear')
        self.generic_put_success('jobs-details', [1], data={'name': 'honey eater',
                                                            'description': 'pooh bear'})
        jd = Job_Definition.objects.get(pk=1)
        self.assertEqual(jd.name, 'honey eater')
        self.assertEqual(jd.description, 'pooh bear')

    def test_job_definition_put_object_failure(self):
        Job_Definition.objects.create(
            name='honey eater', description='pooh bear')
        self.generic_put_failure('jobs-details', [1], data={
            'newname': 'being sad', 'description': 'eyeore'})
        jd = Job_Definition.objects.get(pk=1)
        self.assertEqual(jd.name, 'honey eater')
        self.assertEqual(jd.description, 'pooh bear')
