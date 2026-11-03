import base64
import json
import os
import unittest
from io import BytesIO
from unittest.mock import patch
from app import application, validate_payload, make_pdf


def shipment():
    return {'po': 'TEST-1', 'destination': 'Destino\nDC 1\nCalle\nCiudad', 'pallets': [
        {'size': '40*48*62', 'weight': '142', 'boxes': '18',
         'items': [{'sku': 'SKU-A', 'qty': '36', 'boxes': '18'}, {'sku': 'SKU-B', 'qty': '18', 'share': True}]}]}


class AppTests(unittest.TestCase):
    def request(self, data=None, password='testing-only', authorization=True):
        content = json.dumps(data).encode() if data is not None else b''
        env = {'PATH_INFO': '/generate', 'REQUEST_METHOD': 'POST',
               'CONTENT_LENGTH': str(len(content)), 'wsgi.input': BytesIO(content)}
        if authorization:
            env['HTTP_AUTHORIZATION'] = 'Basic ' + base64.b64encode(b'admin:testing-only').decode()
        status = []
        with patch.dict(os.environ, {'APP_PASSWORD': password}):
            output = b''.join(application(env, lambda s, h: status.append(s)))
        return status[0], output

    def test_dimensions_and_totals(self):
        pallet = validate_payload(shipment())[0]
        self.assertAlmostEqual(pallet['cube'], 68.8888889)
        self.assertEqual(sum(i[1] for i in pallet['items']), 54)
        self.assertEqual(pallet['boxes'], 18)

    def test_reject_missing_or_nonfinite_quantities(self):
        for value in ['', '-1', 'nan', 'inf', '1.5']:
            data = shipment()
            data['pallets'][0]['items'][0]['qty'] = value
            with self.assertRaises(ValueError):
                validate_payload(data)

    def test_explicit_volume_or_calculation(self):
        data = shipment()
        data['pallets'][0]['cube'] = '70,5'
        self.assertEqual(validate_payload(data)[0]['cube'], 70.5)
        data['pallets'][0]['cube'] = ''
        self.assertAlmostEqual(validate_payload(data)[0]['cube'], 68.8888889)
        data['pallets'][0]['cube'] = 'nan'
        with self.assertRaises(ValueError):
            validate_payload(data)

    def test_reject_missing_weight_and_boxes(self):
        for key in ['weight', 'boxes']:
            data = shipment()
            target = data['pallets'][0] if key == 'weight' else data['pallets'][0]['items'][0]
            target[key] = ''
            with self.assertRaises(ValueError):
                validate_payload(data)

    def test_separate_boxes_are_counted_separately(self):
        data = shipment()
        data['pallets'][0]['items'][1].update(share=False, boxes=18)
        pallet = validate_payload(data)[0]
        self.assertEqual(pallet['boxes'], 36)
        self.assertEqual(len(pallet['box_groups']), 2)

    def test_mixed_box_groups(self):
        data = shipment()
        data['pallets'][0]['items'] += [
            {'sku': 'OWN', 'qty': 5, 'boxes': 5},
            {'sku': 'GROUP-2', 'qty': 2, 'boxes': 1},
            {'sku': 'SHARED-2', 'qty': 3, 'share': True}]
        pallet = validate_payload(data)[0]
        self.assertEqual(pallet['boxes'], 24)
        self.assertEqual([(g['start'], g['end']) for g in pallet['box_groups']], [(0, 1), (2, 2), (3, 4)])

    def test_shared_boxes_cannot_be_first_or_repeat_count(self):
        for item_index in [0, 1]:
            data = shipment()
            data['pallets'][0]['items'][item_index].update(share=True, boxes='')
            if item_index == 1:
                data['pallets'][0]['items'][1]['boxes'] = 18
            with self.assertRaises(ValueError):
                validate_payload(data)

    def test_limit_products(self):
        data = shipment(); data['pallets'][0]['items'] *= 8
        with self.assertRaises(ValueError):
            validate_payload(data)

    def test_private_routes(self):
        self.assertTrue(self.request(shipment(), authorization=False)[0].startswith('401'))
        self.assertTrue(self.request(shipment(), password='')[0].startswith('503'))

    def test_generation_endpoint(self):
        status, content = self.request(shipment())
        self.assertEqual(status, '200 OK')
        self.assertTrue(content.startswith(b'%PDF-'))

    def test_bad_payload(self):
        self.assertTrue(self.request({'pallets': []})[0].startswith('400'))
        self.assertTrue(self.request({'pallets': [None]})[0].startswith('400'))


if __name__ == '__main__':
    unittest.main()
