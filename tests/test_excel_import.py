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

    def test_unknown_or_duplicate_headers_request_mapping(self):
        for duplicate in [False, True]:
            b = workbook(); s = b.active
            if duplicate:
                s['H1'] = 'Qty Pcs'
            else:
                s['B1'] = 'dato desconocido'
            self.assertTrue(import_excel(content(b))['needs_mapping'])

    def test_manual_mapping_with_arbitrary_titles(self):
        b = workbook(); s = b.active
        for c in range(1, 8): s.cell(1, c).value = f'Titulo distinto {c}'
        info = import_excel(content(b)); self.assertTrue(info['needs_mapping'])
        result = import_excel(content(b), 0, header_row=1, columns=[1, 2, 3, 4, 5, None, 7])
        self.assertEqual(result['pallets'], 1)
        self.assertEqual(result['rows'][0][0], 'A')

    def test_manual_mapping_rejects_reused_and_invalid_columns(self):
        for columns in [[1, 1, 3, 4, 5, None, 7], [1, 2, 3, 4, 5, None, 100], [1, None, 3, 4, 5, None, 7]]:
            with self.assertRaises(ValueError):
                import_excel(content(workbook()), 0, columns=columns)

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

    def shipments_book(self):
        b = Workbook(); s = b.active
        s.append(['PO', 'Client Order', 'customer', None, 'Item', 'Qty Pcs', '# cartons', 'Qty Pallets', 'Sizes', 'Cube Ft3', 'Weight (Lbs)'])
        s.append([999, 'CLIENT-A', 'CUSTOMER A', 'ADDRESS A\nCITY A', 'SKU-A', 10, '=+F2', 'Pallet 1', '40*48*62', '=40*48*62/1728', 142])
        s.append([None, None, None, None, 'SKU-B', 5, None, None, None, None, None])
        s.append([888, 'CLIENT-B', 'CUSTOMER B', 'ADDRESS B\nCITY B', 'SKU-C', 3, 3, 'Pallet 1', '40*48*84', None, 200])
        for col in ['A', 'B', 'C', 'D', 'H', 'I', 'J', 'K']:
            s.merge_cells(f'{col}2:{col}3')
        return b

    def test_select_shipment_with_merged_metadata_and_restart_pallet_numbers(self):
        b = self.shipments_book()
        result = import_excel(content(b))
        self.assertEqual(len(result['shipments']), 2)
        self.assertEqual([s['po'] for s in result['shipments']], ['CLIENT-A', 'CLIENT-B'])
        first = import_excel(content(b), 0, shipment_index=0)
        second = import_excel(content(b), 0, shipment_index=1)
        self.assertEqual([r[0] for r in first['rows']], ['SKU-A', 'SKU-B'])
        self.assertEqual([r[0] for r in second['rows']], ['SKU-C'])
        self.assertEqual(first['rows'][0][2], '10')
        self.assertEqual(first['pallets'], 1)
        self.assertEqual(second['pallets'], 1)
        self.assertEqual(second['shipment']['destination'], 'ADDRESS B\nCITY B')
        self.assertNotEqual(second['shipment']['po'], '888')

    def test_repeated_po_and_blank_unmerged_client_do_not_split_shipment(self):
        b = self.shipments_book(); s = b.active
        for area in list(s.merged_cells.ranges): s.unmerge_cells(str(area))
        s['B3'] = 'CLIENT-A'
        self.assertEqual(len(import_excel(content(b))['shipments']), 2)

    def test_changed_address_splits_same_client_and_po(self):
        b = self.shipments_book(); s = b.active
        s['B4'] = 'CLIENT-A'; s['C4'] = 'CUSTOMER A'
        result = import_excel(content(b))
        self.assertEqual(len(result['shipments']), 2)
        self.assertNotEqual(result['shipments'][0]['destination'], result['shipments'][1]['destination'])

    def test_invalid_unselected_shipment_does_not_block_good_one(self):
        b = self.shipments_book(); b.active['K4'] = 'BAD'
        self.assertEqual(import_excel(content(b), 0, shipment_index=0)['pallets'], 1)
        with self.assertRaises(ValueError): import_excel(content(b), 0, shipment_index=1)

    def test_aggregate_pallet_quantity_is_not_treated_as_one_pallet(self):
        b = self.shipments_book(); b.active['H4'] = '2 Pallets'
        with self.assertRaisesRegex(ValueError, 'varios pallets'):
            import_excel(content(b), 0, shipment_index=1)

    def test_direct_formula_cycle_is_rejected(self):
        b = self.shipments_book(); b.active['G2'] = '=G2'
        with self.assertRaisesRegex(ValueError, 'circular'):
            import_excel(content(b), 0, shipment_index=0)

    def test_import_endpoint_requires_authentication(self):
        from app import application
        status = []
        body = b''.join(application({'PATH_INFO': '/import-excel', 'REQUEST_METHOD': 'POST'}, lambda s, h: status.append(s)))
        self.assertTrue(status[0].startswith(('401', '503')))


if __name__ == '__main__': unittest.main()
