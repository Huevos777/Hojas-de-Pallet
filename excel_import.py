"""Importación conservadora: encabezados explícitos, sin leer PO ni destino."""
from io import BytesIO
import re
import unicodedata
from zipfile import ZipFile
import openpyxl


TITLES = ['ITEM', 'Qty Pcs', '# Boxes', 'Pallet #', 'Sizes', 'Cube Ft3', 'Weight (Lbs)']
ALIASES = [
    ['item', 'item#', 'sku', 'producto', 'codigo'],
    ['qty pcs', 'qty', 'pcs', 'piezas', 'cantidad'],
    ['# boxes', 'boxes', 'cajas'],
    ['pallet #', 'pallet', 'pallet number', 'tarima'],
    ['sizes', 'size', 'medidas'],
    ['cube ft3', 'cube', 'volumen ft3'],
    ['weight (lbs)', 'weight (lb)', 'peso lbs', 'peso lb'],
]


def normalized(value):
    value = unicodedata.normalize('NFKD', str(value or '').lower())
    return re.sub(r'[^a-z0-9]', '', value)


def import_excel(content, sheet_index=None):
    try:
        with ZipFile(BytesIO(content)) as archive:
            infos = archive.infolist()
            if len(infos) > 3000 or sum(i.file_size for i in infos) > 50*1024*1024:
                raise ValueError('El Excel es demasiado grande. Usa un archivo con solo los datos del envío.')
        book = openpyxl.load_workbook(BytesIO(content), data_only=False)
    except ValueError:
        raise
    except Exception:
        raise ValueError('No pude abrir el archivo. Usa un Excel .xlsx sin contraseña.')
    try:
        candidates = []
        for index, sheet in enumerate(book):
            if sheet.sheet_state != 'visible':
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
                        raise ValueError(f'Hoja {sheet.title}: hay dos columnas de volumen. Deja solo una.')
                    matches.append((row[0].row, mapping))
            if len(matches) > 1:
                raise ValueError(f'Hoja {sheet.title}: encontré varias tablas. Deja una sola tabla por hoja.')
            if matches:
                candidates.append((index, sheet, *matches[0]))
        if not candidates:
            raise ValueError('No encontré una tabla con ITEM, Qty Pcs, # Boxes, Pallet #, Sizes y Weight (Lbs). Revisa los títulos. Cube Ft3 es opcional. Los títulos deben estar en las primeras 50 filas.')
        choices = [{'index': i, 'name': s.title} for i, s, _, _ in candidates]
        if sheet_index is None and len(candidates) > 1:
            return {'sheets': choices}
        selected = candidates[0] if sheet_index is None else next((c for c in candidates if c[0] == sheet_index), None)
        if selected is None:
            raise ValueError('Selecciona una hoja válida del archivo.')
        _, sheet, header, mapping = selected
        if sheet.max_row-header > 2000:
            raise ValueError('La hoja supera 2000 filas. Copia los datos necesarios a un Excel más pequeño.')
        for area in sheet.merged_cells.ranges:
            if area.max_row <= header:
                continue
            if area.max_col > area.min_col and any(area.min_col <= c <= area.max_col for c in mapping.values()):
                raise ValueError('Hay celdas combinadas entre columnas de datos. Separa esas columnas antes de importar.')
            if area.max_row > area.min_row and any(mapping[k] == area.min_col for k in [0, 1]):
                raise ValueError('ITEM o Qty Pcs contiene celdas combinadas. Cada producto debe tener su propia fila y cantidad.')
        rows = []
        for r in range(header+1, sheet.max_row+1):
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
                        row.append(''); continue  # Se calcula con Sizes, no se usa caché de Excel.
                    raise ValueError(f'Fila {r}, {TITLES[k]}: hay una fórmula. En Excel, copia y pega como valores antes de importar.')
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
        return {'rows': rows, 'sheet': sheet.title, 'pallets': len(groups)}
    finally:
        book.close()
