# Hojas de Pallet

Aplicación para cargar un Excel con el formato de `Datos.xlsx` y descargar un PDF tamaño carta con cuatro copias consecutivas de cada pallet.

## Preparación

Requiere Python 3.12.

```sh
cd /workspace/Hojas-de-Pallet
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt
APP_PASSWORD="elige-una-clave-local" .venv/bin/python app.py
```

El servidor utiliza el puerto 8000. Abre la aplicación desde un navegador con acceso a ese servidor. Selecciona el Excel y pulsa «Generar hojas para imprimir». Imprime el PDF con **una sola copia**, pues incluye cuatro por pallet.

## Formato de entrada

Primera fila: PL, Ship To, PO#, ITEM, Qty Pcs, # Boxes, Pallet #, Sizes, Cube Ft3, Weight (Lbs), Total Cube, Total Weight. Se reconocen las celdas combinadas del archivo original. Cada grupo comienza con `Pallet 1`, `Pallet 2 MIX`, etc. Se ignora la fila TOTAL. El volumen se calcula a partir de las medidas cuando no hay un valor calculado guardado en Excel.

El remitente se toma del ejemplo proporcionado y está fijo en esta primera versión. El PDF reproduce sus campos con un diseño propio; revisar la vista previa antes de imprimir. Admite hasta 14 productos por pallet. Los archivos se procesan en memoria. El acceso requiere el usuario `admin` y la contraseña definida en `APP_PASSWORD`. En Internet, usar HTTPS y Gunicorn como indica la configuración de Render.

Los Excel originales del usuario no se incluyen en el repositorio.

## Publicar en Render

Selecciona este repositorio y la rama `main` como Web Service.

- Language: Python 3
- Root Directory: dejar vacío
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:application --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120`
- Health Check Path: `/healthz`
- Environment Variables: `PYTHON_VERSION` = `3.12.8`; `APP_PASSWORD` = una contraseña privada elegida en Render.

No guardar contraseñas en GitHub. El usuario de acceso es `admin`. Render proporciona HTTPS. El plan gratuito puede suspender la aplicación cuando no se usa; comprobar las condiciones actuales en Render. No se requiere base de datos. Los Excel se procesan en memoria y no se guardan. La ruta `/healthz` solo informa del estado del servidor y es pública. Sin `APP_PASSWORD`, las rutas de la aplicación permanecen bloqueadas.

Configura también en Render `SENDER_NAME` (nombre del remitente), `SENDER_ADDRESS` (calle y número), `SENDER_CITY` (ciudad y código postal) y `SENDER_PHONE` (teléfono). Estos datos no se incluyen en GitHub.
