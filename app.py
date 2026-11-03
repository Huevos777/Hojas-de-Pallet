"""Generador local de hojas de pallet. Ejecutar: python3 app.py."""
from io import BytesIO
import os
import base64
import hmac
import binascii
import re
from reportlab.lib.pagesizes import letter


def validate_payload(data):
    import math
    def text(value, label, limit=160):
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f'Revisa {label}: es obligatorio y admite hasta {limit} caracteres.')
        return value.strip()
    def number(value, label, positive=False):
        try:
            result = float(str(value).replace(',', '.'))
        except (ValueError, TypeError):
            raise ValueError(f'Revisa {label}: debe ser un número.')
        if not math.isfinite(result) or result < 0 or (positive and result == 0):
            raise ValueError(f'Revisa {label}: debe ser un número válido mayor que cero.' if positive else f'Revisa {label}: no puede ser negativo.')
        return result
    if not isinstance(data, dict) or not isinstance(data.get('pallets'), list) or not 1 <= len(data['pallets']) <= 100:
        raise ValueError('Agrega entre 1 y 100 pallets.')
    destination = text(data.get('destination'), 'destino', 500)
    if len(destination.splitlines()) > 4 or any(len(line) > 60 for line in destination.splitlines()):
        raise ValueError('El destino admite hasta cuatro líneas de 60 caracteres.')
    po = text(data.get('po'), 'PO', 40)
    pallets = []
    for index, raw in enumerate(data['pallets'], 1):
        if not isinstance(raw, dict):
            raise ValueError('Revisa los datos del pallet.')
        size = text(raw.get('size'), f'medidas del pallet {index}', 40)
        dims = re.split(r'[*xX×]', size)
        if len(dims) != 3:
            raise ValueError(f'Pallet {index}: usa medidas como 40*48*62, en pulgadas.')
        dims = [number(x, 'medidas', True) for x in dims]
        cube = dims[0]*dims[1]*dims[2]/1728
        if raw.get('cube') not in (None, ''):
            cube = number(raw['cube'], f'volumen del pallet {index}', True)
        items = raw.get('items')
        if not isinstance(items, list) or not 1 <= len(items) <= 14:
            raise ValueError(f'Pallet {index}: agrega entre 1 y 14 productos.')
        parsed = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError('Revisa la lista de productos.')
            sku = text(item.get('sku'), 'ITEM', 40)
            qty = number(item.get('qty'), 'piezas', True)
            if not qty.is_integer():
                raise ValueError('La cantidad de piezas debe ser entera.')
            parsed.append((sku, qty, None))
        boxes = number(raw.get('boxes'), f'cajas del pallet {index}', True)
        if not boxes.is_integer():
            raise ValueError('La cantidad de cajas debe ser entera.')
        pallets.append(dict(destination=destination, po=po, size='*'.join(f'{x:g}' for x in dims),
                            cube=cube, weight=number(raw.get('weight'), f'peso del pallet {index}', True),
                            boxes=boxes, items=parsed))
    return pallets


def make_pdf(pallets):
    """Carta, una página por copia; posiciones basadas en Formato.pdf."""
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase.pdfmetrics import stringWidth
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=letter)
    pdf.setTitle('Hojas de Pallet')
    def label(x, top, value, size=18, width=510, center=False):
        value = str(value)
        actual = min(size, size * width / max(stringWidth(value, 'Helvetica-Bold', size), 1))
        pdf.setFont('Helvetica-Bold', actual)
        if center:
            pdf.drawCentredString(x, 792-top, value)
        else:
            pdf.drawString(x, 792-top, value)
    for index, pallet in enumerate(pallets, 1):
        items = pallet['items']
        if len(items) > 14:
            raise ValueError('El máximo es 14 productos por pallet.')
        for _ in range(4):
            label(54.4, 73, 'From:')
            label(310.7, 73, '(619) 661-5592', width=245)
            for top, value in [(100, 'FLORAL TREASURE C/O AM WAREHOUSE'),
                               (127, '8851 kern st suite 200'),
                               (153, 'San Diego, CA, 92154')]:
                label(54.4, top, value)
            label(54.4, 191, 'SHIP TO:')
            pdf.line(54.4, 598, 142, 598)
            destination = pallet['destination'].splitlines()
            label(166, 191, destination[0], 16.2, 390)
            for row, line in enumerate(destination[1:]):
                label(54.4, 218+row*26.6, line)
            for x, title, value in [(107.5,'Size',pallet['size']),(235.4,'Cube Ft3',f"{pallet['cube']:.1f}"),(384.3,'Weight (LB)',f"{pallet['weight']:g}")]:
                label(x, 334, title, width=160, center=True)
                label(x, 361, value, width=160, center=True)
            label(107.4, 413, 'PO #  '+pallet['po'], width=440)
            # Dos productos mantienen exactamente el espacio del ejemplo;
            # listas largas reducen el interlineado y desplazan el pie.
            step = min(26.6, 160/max(len(items)-1, 1))
            font = 18 if len(items) <= 8 else 13
            label(54.4, 440, 'ITEM#', font, 90)
            for row, (sku, qty, _) in enumerate(items):
                top = 440+row*step
                label(184.4, top, sku, font, 116)
                label(310.7, top, f'{qty:g}', font, 45)
                label(360.8, top, 'PCS', font, 46)
            middle = 440+(len(items)-1)*step/2
            label(424.1, middle, f"{pallet['boxes']:g}", width=45)
            label(474.9, middle, 'BOXES', width=85)
            footer = max(520, 440+(len(items)-1)*step+54)
            label(54.4, footer, f'PALLET {index:02d} OF {len(pallets):02d}')
            label(54.4, footer+26.6, f"PIECES PER PALLET: {sum(item[1] for item in items):g}")
            label(54.4, footer+53.2, 'DO NOT BREAK DOWN PALLET &')
            label(54.4, footer+79.8, 'DO NOT STACK ON TOP OF PALLET')
            label(287, footer+106.4, f"{pallet['boxes']:g} BOXES", center=True)
            pdf.showPage()
    pdf.save()
    return output.getvalue()


PAGE = ( __import__('pathlib').Path(__file__).with_name('index.html')).read_text()


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
            raise ValueError('Los datos deben ocupar menos de 10 MB.')
        content = environ['wsgi.input'].read(length)
        import json
        try:
            data = json.loads(content)
        except (ValueError, UnicodeError):
            raise ValueError('No se pudieron leer los datos. Revisa el formulario.')
        result = make_pdf(validate_payload(data))
        return respond('200 OK', result, 'application/pdf',
                       [('Content-Disposition', 'attachment; filename="Hojas-de-Pallet.pdf"')])
    except Exception as exc:
        message = str(exc) if isinstance(exc, ValueError) else 'No se pudieron procesar los datos. Revisa el formulario.'
        return respond('400 Bad Request', message.encode())


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    port = int(os.environ.get('PORT', '8000'))
    print(f'Hojas de Pallet: servidor iniciado en el puerto {port}', flush=True)
    with make_server('0.0.0.0', port, application) as server:
        server.serve_forever()
