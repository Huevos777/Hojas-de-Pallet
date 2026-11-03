# Hojas de Pallet

Aplicación privada para pegar tablas o introducir manualmente productos ya separados por pallet. Genera un PDF carta con una página por pallet. La distribución sigue el PDF de referencia; usa Helvetica Bold, por lo que la tipografía puede variar respecto al original.

## Uso

1. Completa destino (Ship To) y PO# una sola vez, arriba.
2. Escribe o pega la tabla: ITEM, Qty Pcs, # Boxes, Pallet #, Sizes, Cube Ft3, Weight (Lbs). Admite encabezados opcionales de Excel, edición de celdas, Tab, Enter y filas adicionales.
3. Deja Pallet # vacío para continuar el anterior. Escribe # Boxes en el primer producto de cada grupo de cajas. Las celdas de cajas vacías comparten automáticamente las del grupo anterior dentro del mismo pallet. Una nueva cantidad empieza otro grupo propio. El primer producto de cada pallet debe tener cajas; nunca se heredan desde otro pallet.
4. Pulsa «Descargar hojas de pallet». No hay revisión por pallet ni casilla de confirmación. Los datos se procesan directamente desde la tabla; los errores se indican sin generar un PDF incompleto.
5. El PDF contiene una sola página por pallet. Selecciona cuatro copias al imprimir y desactiva «Intercalar» para obtener cuatro hojas juntas por pallet.

Un envío por vez (un PO y un destino). Hasta 2000 filas, 100 pallets y 14 productos por pallet. Medidas en pulgadas y peso en libras. Cube Ft3 se usa si está escrito; si está vacío se calcula con las dimensiones. Los datos no se conservan al recargar la página.

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
