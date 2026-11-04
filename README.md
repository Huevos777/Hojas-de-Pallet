# Hojas de Pallet

Aplicación privada para pegar tablas o introducir manualmente productos ya separados por pallet. Genera un PDF carta con una página por pallet. La distribución sigue el PDF de referencia; usa Helvetica Bold, por lo que la tipografía puede variar respecto al original.

## Uso

1. Completa destino (Ship To) y PO# una sola vez, arriba.
2. Escribe o pega la tabla: ITEM, Qty Pcs, # Boxes, Pallet #, Sizes, Cube Ft3, Weight (Lbs). Admite encabezados opcionales de Excel, edición de celdas, Tab, Enter y filas adicionales.
3. Solo un número distinto en Pallet # empieza otro pallet. Si está vacío o repite el número actual, los productos siguen en el mismo pallet. Sizes, Weight y Cube vacíos conservan los datos de ese pallet; no se heredan datos desde un pallet distinto. Deja Pallet # vacío para continuar el anterior. Escribe # Boxes en el primer producto de cada grupo de cajas. Las celdas de cajas vacías comparten automáticamente las del grupo anterior dentro del mismo pallet. Una nueva cantidad empieza otro grupo propio. El primer producto de cada pallet debe tener cajas; nunca se heredan desde otro pallet.
4. Pulsa «Descargar hojas de pallet». No hay revisión por pallet ni casilla de confirmación. Los datos se procesan directamente desde la tabla; los errores se indican sin generar un PDF incompleto.
5. El PDF contiene una sola página por pallet. Selecciona cuatro copias al imprimir y desactiva «Intercalar» para obtener cuatro hojas juntas por pallet.

Un envío por vez (un PO y un destino). Hasta 2000 filas, 100 pallets y 24 productos por pallet. Medidas en pulgadas y peso en libras. Cube Ft3 se usa si está escrito; si está vacío se calcula con las dimensiones. Los datos no se conservan al recargar la página.

## Importar Excel

También puedes elegir un archivo `.xlsx` desde la sección de productos. La importación llena la misma cuadrícula editable. En archivos simples, no modifica PO# ni destino. Si detecta varios envíos, ofrece elegir uno y usar opcionalmente su PO y dirección. Si ya hay productos, pide confirmación antes de reemplazarlos; un error deja intacta la tabla.

- Se identifican las columnas por títulos, no por posición. Se admiten los encabezados actuales y variantes explícitas como SKU, Piezas, Cajas y Peso (Lbs). Las demás columnas se ignoran.
- Deben existir ITEM, Qty Pcs, # Boxes, Pallet #, Sizes y Weight (Lbs). Cube Ft3 es opcional. Los encabezados deben estar en las primeras 50 filas y 100 columnas. Si un encabezado es desconocido o está duplicado, se abre una vista previa para elegir las columnas manualmente.
- Cuando los títulos cambian, el panel permite elegir hoja, fila de títulos (1–50) y columna para cada dato. «Ver columnas de esta fila» actualiza la muestra; «Importar con estas columnas» valida y carga los productos. No se permite usar una columna dos veces ni omitir datos obligatorios. Cube Ft3 puede calcularse. «Elegir columnas del Excel» abre este modo incluso en archivos reconocidos. Comprueba que las columnas elegidas usan pulgadas y libras: no se convierten otras unidades automáticamente.

- Si varias hojas visibles contienen tablas compatibles, se elige una. No se mezclan envíos ni hojas automáticamente.
- Se respetan celdas combinadas verticalmente en cajas, pallet, medidas, volumen y peso. No se permiten combinaciones en ITEM/piezas ni combinaciones entre columnas de datos.
- Las fórmulas de Cube se omiten y se recalcula el volumen con Sizes. Se evalúan las referencias directas a celdas numéricas de la misma hoja (por ejemplo `=+F37` en cajas), con detección de ciclos. Las demás fórmulas deben convertirse a valores en Excel; no se confía en resultados almacenados potencialmente antiguos.
- Se omiten filas vacías y totales explícitos en ITEM. Se rechazan datos incompletos, errores de Excel y medidas/pesos contradictorios del mismo pallet.
- Se mantienen los ceros iniciales de códigos guardados como texto o con formato numérico compuesto solo por ceros (por ejemplo `000000`). No se reconstruyen ceros que ya se hayan perdido en el archivo.
- Solo `.xlsx` sin contraseña, hasta 32 MB comprimidos y 120 MB descomprimidos, con hasta 2000 filas después del encabezado. Los archivos antiguos `.xls` deben guardarse como `.xlsx`.

El archivo se procesa en memoria y no se conserva. Las validaciones reducen errores de interpretación; no comprueban que los datos del documento correspondan físicamente al envío.

## Excel con varios envíos

- Reconoce `Client Order` / `Cliente Order` como el PO del cliente. Nunca usa la columna `PO` interna para rellenar el PO impreso. `carton` / `cartons` equivalen a cajas; `pallets` / `Qty Pallets` equivalen al identificador de pallet; `Pallet Size` equivale a medidas.
- Después de elegir una hoja, muestra los envíos separados por Client Order, cliente y dirección, respetando las celdas combinadas. Una dirección sin título se propone únicamente si está justo después de customer y contiene varias líneas; se muestra para confirmar al elegir el envío.
- Elige un envío y pulsa **Cargar solo este envío**. Los productos de clientes diferentes no se mezclan aunque ambos tengan Pallet 1.
- La casilla para usar PO y dirección del envío puede desactivarse para conservar los datos manuales. Si está activa, los campos ausentes se vacían para que el usuario los complete y no se reutilice por error una dirección anterior.
- **Elegir otro envío de este Excel** permite trabajar el siguiente cliente sin volver a subir el archivo. No se guarda el Excel en el servidor; cada operación lo envía desde el navegador.
- Las hojas se leen de forma diferida y solo se materializa la elegida (hasta 2000 filas). Así no se cargan completas las hojas históricas grandes ni las imágenes del libro.
- Registros con medidas `BOX` o datos incompletos no generan hojas de pallet hasta completarse. Un texto como `2 Pallets` que resume varios pallets requiere desglosar el reparto: no se divide automáticamente.
- El formato PDF admite hasta 24 productos por pallet; las listas de más de 14 usan una zona de productos ampliada y letra menor.

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
