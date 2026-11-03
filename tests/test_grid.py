"""Regression checks for the browser's table grouping (Node is optional for development)."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'), 'Node no disponible para comprobar la tabla')
class GridTests(unittest.TestCase):
    def prepare(self, rows):
        html = Path(__file__).resolve().parents[1].joinpath('index.html').read_text()
        start = html.index('function prepare()')
        end = html.index('drawSheet();', start)
        script = 'const cells=' + json.dumps(rows) + ';const titles=["ITEM","Qty Pcs","# Boxes","Pallet #","Sizes","Cube Ft3","Weight (Lbs)"];function norm(s){return String(s).toLowerCase().trim()};'
        script += html[start:end] + ';try{console.log(JSON.stringify({pallets:prepare()}))}catch(e){console.log(JSON.stringify({error:e.message}))}'
        result = subprocess.run(['node', '-e', script], text=True, capture_output=True, check=True)
        return json.loads(result.stdout)

    def test_blank_cells_and_repeated_number_stay_in_same_pallet(self):
        result = self.prepare([
            ['A', '36', '18', '2', '40*48*62', '68.9', '142'],
            ['B', '18', '', '', '', '', ''],
            ['', '', '', '', '', '', ''],
            ['C', '10', '', '2', '', '', ''],
        ])['pallets']
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]['items']), 3)
        self.assertEqual((result[0]['size'], result[0]['cube'], result[0]['weight']), ('40*48*62', '68.9', '142'))
        self.assertTrue(all(i['share'] for i in result[0]['items'][1:]))

    def test_only_new_number_starts_new_pallet(self):
        result = self.prepare([
            ['A', '36', '18', '2', '40*48*62', '', '142'],
            ['B', '18', '3', '', '', '', ''],
            ['C', '10', '5', '3', '40*48*84', '', '200'],
            ['D', '5', '', '', '', '', ''],
        ])['pallets']
        self.assertEqual(len(result), 2)
        self.assertEqual([len(p['items']) for p in result], [2, 2])
        self.assertEqual([p['weight'] for p in result], ['142', '200'])
        self.assertFalse(result[0]['items'][1]['share'])
        self.assertTrue(result[1]['items'][1]['share'])

    def test_different_measurement_does_not_silently_start_new_pallet(self):
        result = self.prepare([
            ['A', '36', '18', '2', '40*48*62', '', '142'],
            ['B', '18', '', '', '40*48*84', '', ''],
        ])
        self.assertIn('error', result)

    def test_new_pallet_does_not_inherit_measurements(self):
        result = self.prepare([
            ['A', '36', '18', '2', '40*48*62', '68.9', '142'],
            ['B', '18', '5', '3', '', '', ''],
        ])['pallets']
        self.assertEqual((result[1]['size'], result[1]['cube'], result[1]['weight']), ('', '', ''))

    def test_first_product_requires_pallet_number(self):
        result = self.prepare([['A', '36', '18', '', '40*48*62', '', '142']])
        self.assertIn('error', result)
