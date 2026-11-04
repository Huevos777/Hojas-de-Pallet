# Hojas de Pallet

Aplicación privada para pegar tablas o introducir manualmente productos ya separados por pallet. Genera un PDF carta con una página por pallet. La distribución sigue el PDF de referencia; usa Helvetica Bold, por lo que la tipografía puede variar respecto al original.

## Uso

1. Completa destino (Ship To) y PO# una sola vez, arriba.
2. Escribe o pega la tabla: ITEM, Qty Pcs, # Boxes, Pallet #, Sizes, Cube Ft3, Weight (Lbs). Admite encabezados opcionales de Excel, edición de celdas, Tab, Enter y filas adicionales.
3. Solo un número distinto en Pallet # empieza otro pallet. Si está vacío o repite el número actual, los productos siguen en el mismo pallet. Sizes, Weight y Cube vacíos conservan los datos de ese pallet; no se heredan datos desde un pallet distinto. Deja Pallet # vacío para continuar el anterior. Escribe # Boxes en el primer producto de cada grupo de cajas. Las celdas de cajas vacías comparten automáticamente las del grupo anterior dentro del mismo pallet. Una nueva cantidad empieza otro grupo propio. El primer producto de cada pallet debe tener cajas; nunca se heredan desde otro pallet.
4. Pulsa «Descargar hojas de pallet». No hay revisión por pallet ni casilla de confirmación. Los datos se procesan directamente desde la tabla; los errores se indican sin generar un PDF incompleto.
5. El PDF contiene una sola página por pallet. Selecciona cuatro copias al imprimir y desactiva «Intercalar» para obtener cuatro hojas juntas por pallet.

Un envío por vez (un PO y un destino). Hasta 2000 filas, 100 pallets y 14 productos por pallet. Medidas en pulgadas y peso en libras. Cube Ft3 se usa si está escrito; si está vacío se calcula con las dimensiones. Los datos no se conservan al recargar la página.

## Importar Excel

También puedes elegir un archivo `.xlsx` desde la sección de productos. La importación llena la misma cuadrícula editable: no modifica PO# ni destino, aunque el Excel contenga esas columnas. Si ya hay productos, pide confirmación antes de reemplazarlos; un error deja intacta la tabla.

- Se identifican las columnas por títulos, no por posición. Se admiten los encabezados actuales y variantes explícitas como SKU, Piezas, Cajas y Peso (Lbs). Las demás columnas se ignoran.
- Deben existir ITEM, Qty Pcs, # Boxes, Pallet #, Sizes y Weight (Lbs). Cube Ft3 es opcional. Los encabezados deben estar en las primeras 50 filas y 100 columnas. Un encabezado requerido duplicado o desconocido impide importar.
- Si varias hojas visibles contienen tablas compatibles, se elige una. No se mezclan envíos ni hojas automáticamente.
- Se respetan celdas combinadas verticalmente en cajas, pallet, medidas, volumen y peso. No se permiten combinaciones en ITEM/piezas ni combinaciones entre columnas de datos.
- Las fórmulas de Cube se omiten y se recalcula el volumen con Sizes. Las fórmulas de los demás campos deben convertirse a valores en Excel; no se confía en resultados almacenados potencialmente antiguos.
- Se omiten filas vacías y totales explícitos en ITEM. Se rechazan datos incompletos, errores de Excel y medidas/pesos contradictorios del mismo pallet.
- Se mantienen los ceros iniciales de códigos guardados como texto o con formato numérico compuesto solo por ceros (por ejemplo `000000`). No se reconstruyen ceros que ya se hayan perdido en el archivo.
- Solo `.xlsx` sin contraseña, hasta 10 MB comprimidos y 50 MB descomprimidos, con hasta 2000 filas después del encabezado. Los archivos antiguos `.xls` deben guardarse como `.xlsx`.

El archivo se procesa en memoria y no se conserva. Las validaciones reducen errores de interpretación; no comprueban que los datos del documento correspondan físicamente al envío.

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

La pantalla incluye instrucciones paso a paso y un ejemplo de tres productos que comparten 18 cajas. Las pruebas de agrupación de la tabla usan Node si está disponible; no se requiere Node en producción.
