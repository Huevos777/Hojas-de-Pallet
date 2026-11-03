"""Generador local de hojas de pallet. Ejecutar: python3 app.py."""
from io import BytesIO
import os
import base64
import hmac
import binascii
from xml.sax.saxutils import escape as xml_escape
import re
import openpyxl
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


def read_pallets(content):
    workbook = openpyxl.load_workbook(BytesIO(content), data_only=True)
    pallets = []
    for sheet in workbook:
        if [sheet.cell(1, c).value for c in (1, 3, 4)] != ['PL', 'PO#', 'ITEM']:
            raise ValueError('El archivo debe tener el mismo encabezado que Datos.xlsx: PL, Ship To, PO#, ITEM…')
        current = None
        for row in sheet.iter_rows(min_row=2, values_only=True):
            row = tuple(row) + (None,) * max(0, 12-len(row))
            if row[3] is None:
                continue
            if str(row[3]).strip().upper() == 'TOTAL':
                continue
            if row[6] is not None:
                if not re.fullmatch(r'Pallet\s+\d+(?:\s+MIX)?', str(row[6]).strip(), re.I):
                    raise ValueError('Número de pallet no reconocido: ' + str(row[6]))
                current = dict(number=str(row[6]), destination=str(sheet['B2'].value or ''),
                               po=str(sheet['C2'].value or ''), pl=str(sheet['A2'].value or ''),
                               size=str(row[7] or ''), cube=row[8], weight=row[9], items=[], boxes=0)
                pallets.append(current)
            if row[3] is None:
                continue
            if current is None:
                raise ValueError('Hay productos sin un pallet asignado.')
            if not isinstance(row[4], (int, float)) or row[4] < 0:
                raise ValueError('La cantidad de piezas debe ser un número positivo.')
            if row[5] is not None and (not isinstance(row[5], (int, float)) or row[5] < 0):
                raise ValueError('La cantidad de cajas debe ser un número positivo.')
            current['items'].append((str(row[3]), row[4], row[5]))
            current['boxes'] += row[5] or 0
    if not pallets:
        raise ValueError('No se encontraron pallets en el archivo.')
    return pallets


def make_pdf(pallets):
    output = BytesIO()
    styles = getSampleStyleSheet()
    body = styles['BodyText']; body.fontSize = 12; body.leading = 16
    heading = styles['Heading1']; heading.fontSize = 22
    def p(text, style=body):
        return Paragraph(xml_escape(str(text)).replace('\n', '<br/>'), style)
    story = []
    for index, pallet in enumerate(pallets, 1):
        if len(pallet['items']) > 14:
            raise ValueError('Un pallet tiene más de 14 productos; necesita un formato ampliado antes de imprimir.')
        for copy in range(4):
            if story:
                story.append(PageBreak())
            story += [p('From:  ' + os.environ.get('SENDER_PHONE', '')),
                      p(os.environ.get('SENDER_NAME', 'Remitente')),
                      p(os.environ.get('SENDER_ADDRESS', '')),
                      p(os.environ.get('SENDER_CITY', '')), Spacer(1, 22), p('SHIP TO:', heading),
                      p(pallet['destination']), Spacer(1, 18)]
            cube = pallet['cube']
            if not isinstance(cube, (int, float)):
                dims = re.split(r'[*xX×]', pallet['size'])
                if len(dims) != 3:
                    raise ValueError('No se pudieron leer las medidas del pallet.')
                try:
                    cube = float(dims[0])*float(dims[1])*float(dims[2])/1728
                except ValueError:
                    raise ValueError('Las medidas deben ser tres números, por ejemplo 40*48*84.')
            rows = [['Size', 'Cube Ft3', 'Weight (LB)'], [pallet['size'], f'{cube:.1f}', str(pallet['weight'] or '')]]
            summary = Table(rows, colWidths=[168]*3)
            summary.setStyle(TableStyle([('GRID',(0,0),(-1,-1),1,colors.black),('FONTSIZE',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
            story += [summary, Spacer(1, 16), p('PO #  ' + pallet['po']), Spacer(1, 8)]
            rows = [[p('ITEM#'),p('PCS'),p('BOXES')]]
            for item, qty, boxes in pallet['items']:
                rows.append([p(item.replace(' ', '')),p(f'{qty:g}'),p('' if boxes is None else f'{boxes:g}')])
            table = Table(rows, colWidths=[310,90,104])
            table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),1,colors.black)]))
            story += [table, Spacer(1, 14), p(f'PALLET {index:02d} OF {len(pallets):02d}', heading),
                      p(f"PIECES PER PALLET: {sum(i[1] for i in pallet['items']):g}"),
                      p('DO NOT BREAK DOWN PALLET &'), p('DO NOT STACK ON TOP OF PALLET'),
                      p(f"{pallet['boxes']:g} BOXES", heading)]
    SimpleDocTemplate(output, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=30, bottomMargin=30).build(story)
    return output.getvalue()


PAGE = '''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hojas de Pallet</title>
<style>body{font:18px system-ui;background:#f0f4f8;color:#183247;margin:0}main{max-width:640px;margin:70px auto;padding:32px;background:white;border-radius:16px}button{background:#14664f;color:white;border:0;padding:15px 22px;border-radius:8px;font:inherit;margin-top:24px;cursor:pointer}input{display:block;margin-top:20px;max-width:100%}small{display:block;line-height:1.6;color:#526578}#status{margin-top:20px}</style>
<main><h1>Hojas de Pallet</h1><p>Carga tu Excel de datos y descarga las hojas listas para imprimir.</p><small>Se generan 4 copias consecutivas de cada pallet, en tamaño carta. Usa un archivo con las mismas columnas que Datos.xlsx. El remitente se configura de forma privada en el servidor.</small><form id="form"><input id="file" type="file" accept=".xlsx" required><button id="button">Generar hojas para imprimir</button></form><p id="status" role="status"></p><small>Al imprimir el PDF, selecciona una sola copia: las cuatro copias ya están incluidas. Comprueba la vista previa antes de imprimir.</small></main>
<script>form.onsubmit=async e=>{e.preventDefault();button.disabled=true;document.getElementById('status').textContent='Preparando hojas…';try{let r=await fetch('/generate',{method:'POST',body:document.getElementById('file').files[0]});if(!r.ok)throw Error(await r.text());let u=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=u;a.download='Hojas-de-Pallet.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(u),60000);document.getElementById('status').textContent='PDF generado. Revisa las hojas antes de imprimir.'}catch(e){document.getElementById('status').textContent=e.message}finally{button.disabled=false}};</script></html>'''


def application(environ, start_response):
    def respond(status, content, kind='text/plain; charset=utf-8', extra=()):
        start_response(status, [('Content-Type', kind), ('Content-Length', str(len(content))),
                                ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'), *extra])
        return [content]
    if environ.get('PATH_INFO') == '/healthz' and environ['REQUEST_METHOD'] == 'GET':
        return respond('200 OK', b'ok')
    password = os.environ.get('APP_PASSWORD', '')
    if not password:
        return respond('503 Service Unavailable', 'Falta configurar APP_PASSWORD en el servidor.'.encode())
    try:
        scheme, token = environ.get('HTTP_AUTHORIZATION', '').split(' ', 1)
        user, supplied = base64.b64decode(token, validate=True).decode().split(':', 1)
        valid = scheme.lower() == 'basic' and hmac.compare_digest(user.encode(), b'admin') and hmac.compare_digest(supplied.encode(), password.encode())
    except (ValueError, UnicodeError, binascii.Error):
        valid = False
    if not valid:
        return respond('401 Unauthorized', 'Acceso privado. Introduce tu usuario y contraseña.'.encode(),
                       extra=[('WWW-Authenticate', 'Basic realm="Hojas de Pallet", charset="UTF-8"')])
    path, method = environ.get('PATH_INFO'), environ['REQUEST_METHOD']
    if path == '/' and method == 'GET':
        return respond('200 OK', PAGE.encode(), 'text/html; charset=utf-8')
    if path != '/generate' or method != 'POST':
        return respond('404 Not Found', b'No encontrado')
    try:
        length = int(environ.get('CONTENT_LENGTH') or '0')
        if not 0 < length <= 10 * 1024 * 1024:
            raise ValueError('Selecciona un Excel de hasta 10 MB.')
        content = environ['wsgi.input'].read(length)
        # Limita el tamaño descomprimido de los archivos Excel.
        from zipfile import ZipFile
        with ZipFile(BytesIO(content)) as archive:
            if sum(info.file_size for info in archive.infolist()) > 50 * 1024 * 1024:
                raise ValueError('El Excel es demasiado grande al descomprimirlo.')
        result = make_pdf(read_pallets(content))
        return respond('200 OK', result, 'application/pdf',
                       [('Content-Disposition', 'attachment; filename="Hojas-de-Pallet.pdf"')])
    except Exception as exc:
        message = str(exc) if isinstance(exc, ValueError) else 'No se pudo procesar el Excel. Comprueba que tenga el formato de Datos.xlsx.'
        return respond('400 Bad Request', message.encode())


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    port = int(os.environ.get('PORT', '8000'))
    print(f'Hojas de Pallet: servidor iniciado en el puerto {port}', flush=True)
    with make_server('0.0.0.0', port, application) as server:
        server.serve_forever()
