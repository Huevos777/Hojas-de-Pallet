# Hojas de Pallet

Aplicación privada para pegar tablas o introducir manualmente productos ya separados por pallet. Genera un PDF carta con cuatro copias consecutivas de cada pallet. La distribución sigue el PDF de referencia; usa Helvetica Bold, por lo que la tipografía puede variar respecto al original.

## Uso

1. Completa destino (Ship To) y PO# una sola vez, en Datos del envío.
2. Escribe o pega la tabla con siete columnas fijas: ITEM, Qty Pcs, # Boxes, Pallet #, Sizes, Cube Ft3, Weight (Lbs). Ya no se repiten Ship To y PO# en la cuadrícula.
3. Selecciona la celda inicial y pega desde Excel con Ctrl+V. Admite encabezados opcionales, edición, Tab, Enter y filas adicionales.
4. Pulsa «Revisar pallets de esta tabla». Las filas con Pallet # vacío continúan el anterior. Cada cantidad de # Boxes comienza un grupo de cajas propio; si está vacía, se propone compartir las del producto anterior. Revisa siempre esta propuesta.
5. En cada producto elige **Cajas propias** o **Comparte con el anterior**. Las cajas propias se suman al total. Un producto compartido pertenece al mismo grupo que el anterior, sin volver a sumar cajas. Para un grupo de varios productos en una sola caja, escribe 1 en el primero y marca compartir en los siguientes. Si cada pieza tiene su caja, usa cajas propias e introduce tantas cajas como piezas.
6. El total se calcula desde los grupos; no es un campo editable independiente. El PDF muestra las cajas junto a cada producto/grupo y el total al pie. Al quitar el primer producto de un grupo, el siguiente hereda las cajas del grupo.
7. Confirma la revisión y descarga el PDF. Imprime una sola copia: las cuatro ya están incluidas.

Aplicar la tabla otra vez reemplaza la revisión previa con confirmación. Los cambios en celdas exigen volver a aplicar la tabla. Puedes agregar pallets manualmente.

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
