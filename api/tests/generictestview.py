# General test cases:
# test that get with nothing in the db returns an empty response
# test that get with 1 thing in the db returns one element
# test that get with 2+ things in the db returns multiple elements
# test that post works with valid data
# tests that post doesn't work with invalid data
# test that post doesn't work with data that already exists (if this is the expected behavior, else test that it does work)
# test that get works when you query by primary key
# test that put works when you query by primary key
# test that put doesn't work when you have wrong primary key
# test that get doesn't work when you have worng primary key

from django.urls import reverse
from django.test import TestCase


class GenericTestView(TestCase):

    def generic_get_nothing(self, url_name):
        url = reverse(url_name)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def generic_get_one_item(self, url_name):
        url = reverse(url_name)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        return r
        # self.assertEqual(len(json.loads(r.json())), 1)

    def generic_get_multiple_items(self, url_name, num_items=2):
        url = reverse(url_name)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        return r
        # self.assertEqual(len(json.loads(r.json())), num_items)

    def generic_post_success(self, url_name, data, expected_code=201):
        url = reverse(url_name)
        r = self.client.post(url, data=data, content_type='application/json')
        self.assertEqual(r.status_code, expected_code)

    def generic_post_failure(self, url_name, data, expected_code=400):
        url = reverse(url_name)
        r = self.client.post(url, data=data, content_type='application/json')
        self.assertEqual(r.status_code, expected_code)

    def generic_post_data_already_exists(self, url_name, data):
        url = reverse(url_name)
        r = self.client.post(url, data=data, content_type='application/json')
        self.assertEqual(r.status_code, 400)

    def generic_get_object_exists(self, url_name, args):
        url = reverse(url_name, args=args)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        return r

    def generic_get_object_dne(self, url_name, args):
        url = reverse(url_name, args=args)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def generic_put_success(self, url_name, args, data):
        url = reverse(url_name, args=args)
        r = self.client.put(url, data=data, content_type='application/json')
        self.assertEqual(r.status_code, 200)

    def generic_put_failure(self, url_name, args, data, expected_code=400):
        url = reverse(url_name, args=args)
        r = self.client.put(url, data=data, content_type='application/json')
        self.assertEqual(r.status_code, expected_code)
