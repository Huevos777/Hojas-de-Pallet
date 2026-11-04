from io import BytesIO
import unittest
from openpyxl import Workbook
from excel_import import import_excel


HEADERS = ['ITEM', 'Qty\nPcs', '# Boxes', 'Pallet #', 'Sizes', 'Cube\nFt3', 'Weight (Lbs)']


def workbook():
    book = Workbook(); s = book.active
    s.append(HEADERS)
    s.append(['A', 36, 18, 'Pallet 1', '40*48*62', '=40*48*62/1728', 142])
    s.append(['B', 18, None, None, None, None, None])
    return book


def content(book):
    out = BytesIO(); book.save(out); return out.getvalue()


class ExcelTests(unittest.TestCase):
    def test_merged_shared_boxes_and_formula_volume(self):
        b = workbook(); s = b.active
        for col in ['C', 'D', 'E', 'F', 'G']:
            s.merge_cells(f'{col}2:{col}3')
        result = import_excel(content(b))
        self.assertEqual(result['pallets'], 1)
        self.assertEqual(result['rows'][0], ['A', '36', '18', 'Pallet 1', '40*48*62', '', '142'])
        self.assertEqual(result['rows'][1], ['B', '18', '', '', '', '', ''])

    def test_reordered_columns_and_ignored_shipping_fields(self):
        b = Workbook(); s = b.active
        s.append(['Ship To', 'Weight (Lbs)', 'PO#', 'Pallet #', 'ITEM', '# Boxes', 'Qty Pcs', 'Sizes'])
        s.append(['IGNORAR', 142, 'IGNORAR', 1, 'SKU', 18, 36, '40*48*62'])
        r = import_excel(content(b))
        self.assertEqual(r['rows'][0], ['SKU', '36', '18', '1', '40*48*62', '', '142'])
        self.assertNotIn('IGNORAR', str(r))

    def test_multiple_sheets_require_choice(self):
        b = workbook(); b.copy_worksheet(b.active)
        self.assertEqual(len(import_excel(content(b))['sheets']), 2)
        self.assertEqual(import_excel(content(b), 1)['pallets'], 1)

    def test_missing_or_duplicate_headers_rejected(self):
        for duplicate in [False, True]:
            b = workbook(); s = b.active
            if duplicate:
                s['H1'] = 'Qty Pcs'
            else:
                s['B1'] = 'dato desconocido'
            with self.assertRaises(ValueError): import_excel(content(b))

    def test_formula_quantities_rejected(self):
        b = workbook(); b.active['B2'] = '=18*2'
        with self.assertRaisesRegex(ValueError, 'fórmula'): import_excel(content(b))

    def test_missing_values_and_different_weights_rejected(self):
        for cell, value in [('B2', None), ('G2', None), ('G3', 200), ('C2', None)]:
            b = workbook(); b.active[cell] = value
            with self.assertRaises(ValueError): import_excel(content(b))

    def test_leading_zero_sku_preserved(self):
        b = workbook(); b.active['A2'] = 123; b.active['A2'].number_format = '000000'
        self.assertEqual(import_excel(content(b))['rows'][0][0], '000123')

    def test_totals_skipped(self):
        b = workbook(); b.active.append(['TOTAL', 54, 18, 'Pallets: 1', None, '=SUM(F2:F3)', 142])
        self.assertEqual(len(import_excel(content(b))['rows']), 2)

    def test_cross_column_merges_rejected(self):
        b = workbook(); b.active.merge_cells('D2:E2')
        with self.assertRaisesRegex(ValueError, 'combinadas'): import_excel(content(b))

    def test_invalid_file_rejected(self):
        with self.assertRaises(ValueError): import_excel(b'not an xlsx')

    def test_import_endpoint_requires_authentication(self):
        from app import application
        status = []
        body = b''.join(application({'PATH_INFO': '/import-excel', 'REQUEST_METHOD': 'POST'}, lambda s, h: status.append(s)))
        self.assertTrue(status[0].startswith(('401', '503')))


if __name__ == '__main__': unittest.main()
