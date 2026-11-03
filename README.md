# Hojas de Pallet

Aplicación privada para pegar tablas o introducir manualmente productos ya separados por pallet. Genera un PDF carta con cuatro copias consecutivas de cada pallet. La distribución sigue el PDF de referencia; usa Helvetica Bold, por lo que la tipografía puede variar respecto al original.

## Uso

1. Introduce PO y destino (hasta cuatro líneas).
2. Pega una tabla con encabezados opcionales, selecciona su separador y relaciona las columnas. Acepta tabulaciones de Excel, CSV, punto y coma, barras verticales y columnas separadas por dos o más espacios. Los nombres de columna habituales se proponen automáticamente, pero deben revisarse.
3. Importa los pallets y revisa productos, piezas, cajas, medidas en pulgadas y peso en libras. Se conservan las celdas de pallet vacías como continuación del anterior. Las cajas de las filas se suman: si el origen repite el total en cada fila, corrige el total antes de generar. No se infieren cajas a partir de piezas.
4. También puedes crear, editar o eliminar pallets y productos manualmente.
5. Confirma la revisión y descarga el PDF. Imprime una sola copia: las cuatro ya están incluidas.

No interpreta automáticamente texto libre arbitrario ni reparte productos entre pallets. Cuando la tabla no se puede identificar, usa la asignación de columnas o la entrada manual. Un envío por vez (un PO y un destino). Hasta 100 pallets y 14 productos por pallet; las listas largas usan texto más pequeño sin dividir la página. El volumen se calcula a partir de las tres dimensiones.

## Desarrollo

Python 3.12:

```sh
cd /workspace/Hojas-de-Pallet
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt
```

Configura `APP_PASSWORD` en el entorno del proceso y ejecuta `.venv/bin/python app.py`. El servidor local escucha en el puerto 8000 (o `PORT`). El usuario es `admin`. Para producción usa Gunicorn, como indica `render.yaml`.

## Render

- Rama: `main`; directorio raíz vacío; runtime Python 3.
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:application --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120`
- Health Check: `/healthz`
- Variables privadas: `APP_PASSWORD`, `SENDER_NAME`, `SENDER_ADDRESS`, `SENDER_CITY`, `SENDER_PHONE`.

No guardar valores privados en GitHub. Render proporciona HTTPS. Las rutas de la aplicación se bloquean sin contraseña; `/healthz` es público y solo responde `ok`. Los datos se procesan en memoria, sin guardarse en disco ni en registros de aplicación. No se incluye ningún archivo original del usuario en GitHub. Los procesos deben reiniciarse después de restaurar un entorno.

## Validación

```sh
python3 -m unittest discover -s tests -v
```

Se probó además el flujo de pegado, edición y descarga con Chromium/Playwright y la estructura del PDF con un lector PDF. Estas herramientas no son necesarias en producción.
