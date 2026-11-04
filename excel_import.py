"""Importación conservadora con selección de hoja, columnas y envío."""
from io import BytesIO
import re
import unicodedata
from zipfile import ZipFile
import openpyxl


TITLES = ['ITEM', 'Qty Pcs', '# Boxes', 'Pallet #', 'Sizes', 'Cube Ft3', 'Weight (Lbs)']
ALIASES = [
    ['item', 'item#', 'sku', 'producto', 'codigo'],
    ['qty pcs', 'qty', 'pcs', 'piezas', 'cantidad'],
    ['# boxes', 'boxes', 'cajas', 'carton', 'cartons', '# cartons'],
    ['pallet #', 'pallet', 'pallet number', 'tarima', 'pallets', 'qty pallets'],
    ['sizes', 'size', 'medidas', 'pallet size'],
    ['cube ft3', 'cube', 'volumen ft3'],
    ['weight (lbs)', 'weight (lb)', 'peso lbs', 'peso lb'],
]


def normalized(value):
    value = unicodedata.normalize('NFKD', str(value or '').lower())
    return re.sub(r'[^a-z0-9]', '', value)


def import_excel(content, sheet_index=None, *, inspect=False, header_row=1, columns=None, shipment_index=None):
    try:
        with ZipFile(BytesIO(content)) as archive:
            infos = archive.infolist()
            if len(infos) > 3000 or sum(i.file_size for i in infos) > 120*1024*1024:
                raise ValueError('El Excel es demasiado grande. Usa un archivo con solo los datos del envío.')
        book = openpyxl.load_workbook(BytesIO(content), data_only=False, read_only=True)
    except ValueError:
        raise
    except Exception:
        raise ValueError('No pude abrir el archivo. Usa un Excel .xlsx sin contraseña.')
    try:
        visible = [(i, sheet) for i, sheet in enumerate(book) if sheet.sheet_state == 'visible']
        def preview():
            selected = next(((i, s) for i, s in visible if i == sheet_index), None) if sheet_index is not None else (visible[0] if visible else None)
            if selected is None:
                raise ValueError('Selecciona una hoja visible válida.')
            i, sheet = selected
            if not isinstance(header_row, int) or not 1 <= header_row <= min(sheet.max_row, 50):
                raise ValueError('La fila de títulos debe estar entre 1 y 50 y existir en la hoja.')
            width = min(sheet.max_column, 100)
            titles = [str(sheet.cell(header_row, c).value or '')[:200] for c in range(1, width+1)]
            samples = [[str(sheet.cell(r, c).value or '')[:200] for c in range(1, width+1)]
                       for r in range(header_row+1, min(sheet.max_row, header_row+4)+1)]
            suggestions = []
            for aliases in ALIASES:
                matches = [c+1 for c, title in enumerate(titles) if normalized(title) in [normalized(a) for a in aliases]]
                suggestions.append(matches[0] if len(matches) == 1 else None)
            return dict(needs_mapping=True, sheets=[dict(index=i, name=s.title) for i, s in visible],
                        selected_sheet=i, header_row=header_row, headers=titles, samples=samples, suggestions=suggestions)
        if inspect:
            return preview()
        if columns is not None:
            info = preview()
            if not isinstance(columns, list) or len(columns) != 7:
                raise ValueError('Selecciona las columnas de la tabla.')
            if any(c is not None and (type(c) is not int or not 1 <= c <= len(info['headers'])) for c in columns):
                raise ValueError('Una columna seleccionada no existe.')
            mapping = {k: c for k, c in enumerate(columns) if c is not None}
            if not all(k in mapping for k in [0, 1, 2, 3, 4, 6]):
                raise ValueError('Selecciona todas las columnas obligatorias. Solo Cube Ft3 puede omitirse.')
            if len(set(mapping.values())) != len(mapping):
                raise ValueError('Cada columna de Excel debe usarse una sola vez.')
            sheet = book.worksheets[info['selected_sheet']]
            header = header_row
        else:
            candidates = []
            ambiguous = set()
            for index, sheet in enumerate(book):
                if sheet.sheet_state != 'visible' or (sheet_index is not None and index != sheet_index):
                    continue
                matches = []
                for row in sheet.iter_rows(min_row=1, max_row=min(sheet.max_row, 50), max_col=min(sheet.max_column, 100)):
                    mapping = {}
                    for cell in row:
                        key = normalized(cell.value)
                        for field, aliases in enumerate(ALIASES):
                            if key and key in [normalized(a) for a in aliases]:
                                if field in mapping:
                                    mapping[field] = None
                                else:
                                    mapping[field] = cell.column
                    if all(mapping.get(k) for k in [0, 1, 2, 3, 4, 6]):
                        if 5 in mapping and mapping[5] is None:
                            continue
                        matches.append((row[0].row, mapping))
                if len(matches) > 1:
                    ambiguous.add(index)
                if matches:
                    candidates.append((index, sheet, *matches[0]))
            if not candidates:
                return preview()
            choices = [{'index': i, 'name': s.title} for i, s, _, _ in candidates]
            if sheet_index is None and len(candidates) > 1:
                return {'sheets': choices}
            selected = candidates[0] if sheet_index is None else next((c for c in candidates if c[0] == sheet_index), None)
            if selected is None:
                raise ValueError('Selecciona una hoja válida del archivo.')
            if selected[0] in ambiguous:
                return preview()
            _, sheet, header, mapping = selected
        if sheet.max_row-header > 2000:
            raise ValueError('La hoja supera 2000 filas. Copia los datos necesarios a un Excel más pequeño.')
        # Solo materializamos la hoja elegida: otras hojas pueden contener miles de filas.
        from xml.etree.ElementTree import iterparse
        chosen_index = book.worksheets.index(sheet)
        fresh = openpyxl.Workbook()
        materialized = fresh.active
        materialized.title = sheet.title
        for source_row in sheet.iter_rows(max_row=sheet.max_row, max_col=min(sheet.max_column, 100)):
            for cell in source_row:
                if cell.value is not None:
                    target = materialized.cell(cell.row, cell.column, cell.value)
                    target.number_format = cell.number_format
                    target.data_type = cell.data_type
        with ZipFile(BytesIO(content)) as archive:
            with archive.open(sheet._worksheet_path) as xml:
                for _, element in iterparse(xml, events=['end']):
                    if element.tag.endswith('}mergeCell'):
                        materialized.merge_cells(element.attrib['ref'])
                    element.clear()
        sheet = materialized
        def value_at(row, col):
            cell = sheet.cell(row, col)
            if cell.value is None:
                for area in sheet.merged_cells.ranges:
                    if area.min_row <= row <= area.max_row and area.min_col <= col <= area.max_col:
                        cell = sheet.cell(area.min_row, area.min_col)
                        break
            if cell.data_type in ('f', 'e'):
                raise ValueError(f'{cell.coordinate}: el cliente, PO o dirección no puede contener fórmulas ni errores.')
            value = cell.value
            return '' if value is None else str(int(value) if isinstance(value, float) and value.is_integer() else value).strip()
        header_cells = list(sheet.iter_rows(min_row=header, max_row=header, max_col=min(sheet.max_column,100)))[0]
        def metadata_column(aliases):
            matches = [c.column for c in header_cells if normalized(c.value) in aliases]
            if len(matches) > 1:
                raise ValueError('Hay columnas de envío duplicadas. Deja un solo Client Order, cliente y dirección.')
            return matches[0] if matches else None
        po_col = metadata_column(['clientorder', 'clienteorder', 'clientpo', 'customerpo', 'ordendelcliente'])
        client_col = metadata_column(['customer', 'cliente', 'client', 'nombre del cliente'.replace(' ', '')])
        address_col = metadata_column(['shippingaddress', 'shipto', 'direccion', 'direcciondeenvio', 'destination'])
        if not address_col and client_col:
            # Solo propone una columna sin título que contenga direcciones multilínea.
            nearby = client_col+1
            if nearby not in mapping.values() and not sheet.cell(header, nearby).value:
                if any(len(value_at(r, nearby).splitlines()) >= 2 for r in range(header+1, min(sheet.max_row,header+30)+1)):
                    address_col = nearby
        shipments = []
        if po_col or client_col:
            active = None
            lookup = {}
            for r in range(header+1, sheet.max_row+1):
                sku = sheet.cell(r, mapping[0]).value
                if sku is None or normalized(sku) in ('total','totales','grandtotal'):
                    continue
                meta = (value_at(r, po_col) if po_col else '', value_at(r, client_col) if client_col else '', value_at(r, address_col) if address_col else '')
                if any(meta):
                    # No arrastrar una dirección a un pedido nuevo si está ausente.
                    if active is None or any(value and value != active['key'][i] for i, value in enumerate(meta)):
                        if meta not in lookup:
                            active = dict(key=meta, rows=[], po=meta[0], customer=meta[1], destination=meta[2])
                            lookup[meta] = active
                            shipments.append(active)
                        else:
                            active = lookup[meta]
                if active is None:
                    active = dict(key=('', '', ''), rows=[], po='', customer='', destination='')
                    shipments.append(active)
                active['rows'].append(r)
            if shipments and shipment_index is None:
                return dict(shipments=[dict(index=i, po=p['po'], customer=p['customer'], destination=p['destination'], products=len(p['rows'])) for i,p in enumerate(shipments)], selected_sheet=chosen_index,
                            header_row=header, columns=[mapping.get(k) for k in range(7)])
            if shipment_index is not None:
                if type(shipment_index) is not int or not 0 <= shipment_index < len(shipments):
                    raise ValueError('Selecciona un envío válido.')
                selected_shipment = shipments[shipment_index]
            else:
                selected_shipment = None
        else:
            if shipment_index is not None:
                raise ValueError('La hoja no contiene envíos separados para seleccionar.')
            selected_shipment = None
        selected_rows = set(selected_shipment['rows']) if selected_shipment else set(range(header+1, sheet.max_row+1))
        for area in sheet.merged_cells.ranges:
            if not any(area.min_row <= r <= area.max_row for r in selected_rows):
                continue
            if area.max_col > area.min_col and any(area.min_col <= c <= area.max_col for c in mapping.values()):
                raise ValueError('Hay celdas combinadas entre columnas de datos. Separa esas columnas antes de importar.')
            if area.max_row > area.min_row and any(mapping[k] == area.min_col for k in [0, 1]):
                raise ValueError('ITEM o Qty Pcs contiene celdas combinadas. Cada producto debe tener su propia fila y cantidad.')
        rows = []
        for r in sorted(selected_rows):
            source = [sheet.cell(r, mapping[k]) if k in mapping else None for k in range(7)]
            if normalized(source[0].value) in ['total', 'totales', 'grandtotal']:
                continue
            if not any(c is not None and c.value is not None and str(c.value).strip() for c in source):
                continue
            row = []
            for k, cell in enumerate(source):
                if cell is None or cell.value is None:
                    row.append(''); continue
                if cell.data_type == 'f':
                    if k == 5:
                        row.append(''); continue
                    # Evalúa únicamente copias directas de celdas numéricas de esta hoja.
                    seen = set()
                    reference = cell
                    while reference.data_type == 'f':
                        if reference.coordinate in seen:
                            raise ValueError(f'Fila {r}: fórmula circular.')
                        seen.add(reference.coordinate)
                        match = re.fullmatch(r'=\+?\s*(\$?[A-Z]{1,3}\$?[1-9][0-9]*)\s*', reference.value, re.I)
                        if not match:
                            raise ValueError(f'Fila {r}, {TITLES[k]}: fórmula no compatible. En Excel pega esa columna como valores.')
                        reference = sheet[match[1].replace('$','')]
                    if not isinstance(reference.value, (int, float)) or isinstance(reference.value, bool):
                        raise ValueError(f'Fila {r}: la fórmula no apunta a una cantidad numérica.')
                    cell = reference
                if cell.data_type == 'e' or isinstance(cell.value, bool):
                    raise ValueError(f'Fila {r}, {TITLES[k]}: contiene un error o un valor no válido.')
                value = cell.value
                if isinstance(value, (float, int)):
                    if k == 0 and re.fullmatch(r'0+', cell.number_format) and float(value).is_integer():
                        value = str(int(value)).zfill(len(cell.number_format))
                    elif float(value).is_integer():
                        value = str(int(value))
                row.append(str(value).strip())
            if not row[0]:
                raise ValueError(f'Fila {r}: falta ITEM. Cada fila con datos debe tener un producto.')
            if re.fullmatch(r'(?:[2-9]|[1-9][0-9]+)\s+pallets?', row[3], re.I):
                raise ValueError(f'Fila {r}: «{row[3]}» indica varios pallets juntos. Separa sus productos por pallet antes de importar; no se puede adivinar el reparto.')
            rows.append(row)
        if not rows:
            raise ValueError('La hoja no contiene productos debajo de los títulos.')
        # Valida con las mismas reglas de generación, sin tomar datos del envío del Excel.
        from app import validate_payload
        groups = {}
        current = ''
        for i, row in enumerate(rows, 1):
            if row[3]:
                current = row[3]
            if not current:
                raise ValueError(f'Producto {i}: falta el primer Pallet #.')
            p = groups.setdefault(current, dict(size='', cube='', weight='', items=[]))
            for field, col in [('size', 4), ('cube', 5), ('weight', 6)]:
                if row[col]:
                    if p[field] and p[field] != row[col]:
                        raise ValueError(f'Pallet {current}: hay valores diferentes en {TITLES[col]}.')
                    p[field] = row[col]
            p['items'].append(dict(sku=row[0], qty=row[1], boxes=row[2]))
        validate_payload(dict(po='validacion', destination='validacion', pallets=list(groups.values())))
        result = {'rows': rows, 'sheet': sheet.title, 'pallets': len(groups)}
        if selected_shipment:
            result['shipment'] = {k: selected_shipment[k] for k in ['po', 'customer', 'destination']}
        return result
    finally:
        book.close()
