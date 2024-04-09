
from api.tests.generictestview import GenericTestView
from api.models import Region


class TestRegionViews(GenericTestView):

    def test_region_get_empty(self):
        self.generic_get_nothing('regions-list')

    def test_region_get_one(self):
        Region.objects.create(
            code='UB', description='UGABOOGABOOGA', namespace='')
        resp = self.generic_get_one_item('regions-list')
        self.assertIn('UGABOOGABOOGA', resp.content.decode())

    def test_region_get_multi(self):
        Region.objects.create(
            code='UB', description='UGABOOGABOOGA1', namespace='')
        Region.objects.create(
            code='UB3', description='UGABOOGABOOGA, UGABOOGA', namespace='UGA')
        resp = self.generic_get_multiple_items('regions-list')
        self.assertIn('UGABOOGABOOGA1', resp.content.decode())
        self.assertIn('UGABOOGABOOGA, UGABOOGA', resp.content.decode())

    def test_region_post_success(self):
        data = {
            "code": "EU.CARDIFF",
            "description": "CARDIFF",
            "namespace": "county",
        }
        region_count = Region.objects.all().count()
        self.assertEqual(region_count, 0)
        self.generic_post_success('regions-list', data)
        region_count = Region.objects.all().count()
        self.assertEqual(region_count, 1)

    def test_region_post_failure(self):
        data = {
            "Wubbalubbadubdub": "EU.CARDIFF",
            "description": "rubber duckie",
            "namespace": "bathtub",
        }
        region_count = Region.objects.all().count()
        self.assertEqual(region_count, 0)
        self.generic_post_failure('regions-list', data)
        region_count = Region.objects.all().count()
        self.assertEqual(region_count, 0)

    def test_region_post_failure_already_exists(self):
        Region.objects.create(
            code='EU.CARDIFF', description='CARDIFF', namespace='Whatever')
        data = {
            "code": "EU.CARDIFF",
            "description": "CARDIFF",
            "namespace": "Whatever",
        }
        region_count = Region.objects.all().count()
        self.assertEqual(region_count, 1)
        self.generic_post_data_already_exists('regions-list', data)
        region_count = Region.objects.all().count()
        self.assertEqual(region_count, 1)

    def test_region_get_object(self):
        Region.objects.create(
            code='EU.CARDIFF', description='CARDIFF', namespace='Whatever')
        resp = self.generic_get_object_exists(
            'regions-details', ['EU.CARDIFF'])
        self.assertIn('EU.CARDIFF', resp.content.decode())

    def test_region_get_object_fail(self):
        Region.objects.create(
            code='EU.CARDIFF', description='CARDIFF', namespace='Whatever')
        self.generic_get_object_dne('regions-details', ['Porridge'])

    def test_region_put_object_success(self):
        Region.objects.create(
            code='EU.CARDIFF', description='CARDIFF', namespace='Whatever')
        self.generic_put_success('regions-details', ['EU.CARDIFF'], data={'code': 'EU.CARDIFF',
                                                                          'description': 'NEW CARDIFF', 'namespace': 'EVER'})
        r = Region.objects.get(code='EU.CARDIFF')
        self.assertEqual(r.description, 'NEW CARDIFF')
        self.assertEqual(r.namespace, 'EVER')

    def test_region_put_object_success2(self):
        Region.objects.create(
            code='EU.CARDIFF', description='CARDIFF', namespace='Whatever')
        self.generic_put_success('regions-details', ['EU.CARDIFF'], data={'code': 'EU.CARDIFF',
                                                                          'thisisnotarealfield!': 'NEW CARDIFF', 'namespace': 'EVER'})
        r = Region.objects.get(code='EU.CARDIFF')
        self.assertEqual(r.description, 'CARDIFF')
        self.assertEqual(r.namespace, 'EVER')

    def test_region_put_object_failure(self):
        Region.objects.create(
            code='EU.CARDIFF', description='CARDIFF', namespace='Whatever')
        self.generic_put_failure('regions-details', ['EU.CARDIFF'], data={
            'description-ay': 'NEW CARDIFF', 'namespace': 'EVER'})
        r = Region.objects.get(code='EU.CARDIFF')
        self.assertEqual(r.description, 'CARDIFF')
        self.assertEqual(r.namespace, 'Whatever')

    def test_region_put_object_success_change_pk(self):
        Region.objects.create(
            code='EU.CARDIFF', description='CARDIFF', namespace='Whatever')
        self.generic_put_success('regions-details', ['EU.CARDIFF'], data={'code': 'UGABOOGA',
                                                                          'description': 'NEW CARDIFF', 'namespace': 'EVER'})
        r = Region.objects.get(code='UGABOOGA')
        self.assertEqual(r.description, 'NEW CARDIFF')
        self.assertEqual(r.namespace, 'EVER')
        r_count = Region.objects.count()
        self.assertEqual(r_count, 1)
