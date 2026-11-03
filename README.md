# Hojas de Pallet

Aplicación privada para pegar tablas o introducir manualmente productos ya separados por pallet. Genera un PDF carta con cuatro copias consecutivas de cada pallet. La distribución sigue el PDF de referencia; usa Helvetica Bold, por lo que la tipografía puede variar respecto al original.

## Uso

1. Escribe o pega en la cuadrícula con estas nueve columnas fijas, en este orden: Ship To, PO#, ITEM, Qty Pcs, # Boxes, Pallet #, Sizes, Cube Ft3, Weight (Lbs).
2. Selecciona la celda inicial y pega un bloque de Excel con Ctrl+V. Admite encabezados opcionales en ese mismo orden y direcciones multilínea entre comillas como las copia Excel. También puedes editar cada celda, usar Tab y Enter, y agregar filas. Shift+Enter permite varias líneas en una celda.
3. Pulsa «Revisar pallets de esta tabla». Ship To y PO# se trasladan al envío; las filas con Pallet # vacío continúan el anterior. Las cajas de las filas se suman: no repitas un total en cada producto. No se infieren cajas a partir de piezas. Se omiten filas vacías y filas ITEM = TOTAL.
4. Revisa o corrige cada pallet. Aplicar la tabla otra vez reemplaza la revisión previa con confirmación. Cualquier cambio en las celdas exige volver a aplicar la tabla antes de generar. También puedes agregar pallets manualmente.
5. Confirma la revisión y descarga el PDF. Imprime una sola copia: las cuatro ya están incluidas.

Un envío por vez (un PO y un destino). Hasta 2000 filas en la cuadrícula, 100 pallets y 14 productos por pallet. Las medidas van en pulgadas y el peso en libras. Cube Ft3 se usa cuando lo escribes; si está vacío se calcula con las tres dimensiones. Las listas largas usan texto más pequeño sin dividir la página. Los datos no se conservan al recargar la página.

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
- Variable privada: `APP_PASSWORD`.
- Remitente fijo autorizado por el usuario: FLORAL TREASURE C/O AM WAREHOUSE, 8851 kern st suite 200, San Diego, CA, 92154; (619) 661-5592. Ya no requiere variables `SENDER_*`.

No guardar valores privados en GitHub. Render proporciona HTTPS. Las rutas de la aplicación se bloquean sin contraseña; `/healthz` es público y solo responde `ok`. Los datos se procesan en memoria, sin guardarse en disco ni en registros de aplicación. No se incluye ningún archivo original del usuario en GitHub. Los procesos deben reiniciarse después de restaurar un entorno.

## Validación

```sh
python3 -m unittest discover -s tests -v
```

Se probó además el flujo de pegado, edición y descarga con Chromium/Playwright y la estructura del PDF con un lector PDF. Estas herramientas no son necesarias en producción.
