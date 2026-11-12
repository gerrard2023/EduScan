# EduScan v1 - Digitalización y calificación de exámenes

Aplicación web educativa para PC y celular, construida con **Python + Streamlit + OpenCV + Tesseract OCR**.

## Funciones reales de esta primera versión

1. Reconocer texto en fotografías (JPG/PNG) y PDF, incluidos PDF escaneados.
2. Corregir el texto reconocido en la interfaz y descargarlo en **Word DOCX** y TXT.
3. Crear e imprimir hojas de respuestas estandarizadas A4 de **5, 10, 15 o 20** preguntas, con cuatro alternativas (A-D).
4. Registrar una clave de respuestas y leer hojas completadas mediante una fotografía de celular.
5. Revisar respuestas en blanco o múltiples, corregir selecciones y obtener nota sobre 10.
6. Ver y descargar el registro temporal de calificaciones en CSV compatible con Excel.

**Limitaciones:** no califica preguntas abiertas ni genera preguntas automáticamente; tampoco lee cualquier diseño de hoja. El OMR solo funciona con la plantilla EduScan v1 sin modificaciones, impresa en A4, y fotografías nítidas donde se ven los cuatro cuadrados negros. Ante luz deficiente o errores de alineación hay que repetir la foto. No tiene cuentas de usuario ni base de datos: no usar datos identificables reales en un despliegue público sin implementar primero autenticación y medidas legales de protección de datos.

## Paso 1. Instalar lo necesario

Usa **Python 3.11 o 3.12**. Instala [Python](https://www.python.org/downloads/) y [Tesseract OCR](https://github.com/tesseract-ocr/tesseract).

En **Windows**, instala Tesseract con los paquetes de idioma **Spanish** e **English**. Añade su carpeta (por ejemplo, `C:\Program Files\Tesseract-OCR`) a la variable de entorno `PATH`. Abre una terminal nueva y ejecuta `tesseract --list-langs`; deben aparecer `spa` y `eng`.

En **Ubuntu/Debian**:

```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng
```

En **macOS (Homebrew)**:

```bash
brew install tesseract tesseract-lang
```

## Paso 2. Instalar las dependencias Python

Extrae el ZIP en una carpeta. Abre una terminal o PowerShell dentro de `EduScan_v1`.

En **Windows**:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Si PowerShell no permite activar el entorno, ejecuta directamente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

En **Linux / macOS**:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

El navegador normalmente abrirá `http://localhost:8501`.

## Paso 3. Usar la aplicación

1. En **Hoja y clave**, elige el número de preguntas y rellena la clave correcta.
2. Descarga la **hoja de respuestas A4** e imprímela a tamaño real, sin recortes.
3. Pide a los estudiantes marcar un único círculo por pregunta con tinta oscura.
4. En **Calificar**, sube la foto o usa la cámara. Asegúrate de fotografiar toda la hoja sin tapar los marcadores de esquina.
5. Revisa opciones detectadas y corrige cualquier marca dudosa, antes de añadir la nota.
6. En **Resultados**, descarga el archivo CSV antes de cerrar la sesión.
7. En **Digitalizar examen**, carga el examen, reconoce el texto y descárgalo en Word.

**Recomendación:** antes de usarlo con alumnos, prueba con la `ejemplos/hoja_prueba_10p.pdf` y `ejemplos/respuestas_marcadas_10p.png`. La clave correcta de esta demostración es `B,A,C,D,B,C,A,D,B,C` y la foto de ejemplo simula las respuestas `B,A,C,D,B,C,A,D,A,C`, por lo que debe dar **9,00 / 10**. El caso de prueba permite detectar errores en el entorno.

## Paso 4. Usar desde el celular

- Si se ejecuta en tu computadora, conecta el celular a la **misma red Wi-Fi**.
- Busca la dirección IP local de la computadora (en Windows, `ipconfig`).
- Inicia el servidor con:

```bash
python -m streamlit run app.py --server.address 0.0.0.0
```

- En el celular, visita `http://IP-DE-TU-PC:8501`, por ejemplo `http://192.168.1.20:8501` (sustituye esta IP ilustrativa por la de tu equipo).
- El firewall puede requerir permitir el puerto 8501. No expongas este puerto directamente a Internet. Para cámara integrada, el navegador puede requerir HTTPS; si el permiso falla usa **Subir imagen** tras tomarla con la aplicación de cámara del teléfono.

## Paso 5. Publicar una demo web (sin datos reales)

1. Sube el contenido de `EduScan_v1` a un repositorio GitHub (sin datos estudiantiles).
2. En [share.streamlit.io](https://share.streamlit.io), crea una nueva aplicación conectada a ese repositorio.
3. Archivo de entrada: `app.py`; elige Python 3.11 o 3.12 si está disponible.
4. La plataforma instalará las bibliotecas de `requirements.txt` y los paquetes de Linux de `packages.txt`, incluidos los idiomas OCR.
5. Abre el enlace en tu computadora o celular. **Solo pruebas con datos ficticios**, pues esta demo no tiene autenticación ni almacenamiento protegido.

## Archivos del proyecto

```text
EduScan_v1/
  app.py                 Interfaz web
  omr.py                 Reconocimiento de casillas
  plantilla.py           Plantilla PDF A4
  digitalizador.py       OCR y exportación Word
  requirements.txt       Dependencias Python
  packages.txt           Dependencias sistema Linux
  .streamlit/config.toml Apariencia y tamaño de subida
  tests/test_core.py     Pruebas automáticas
  ejemplos/               Plantillas y archivos de prueba
```

## Solución de problemas

- **No se detectan cuatro cuadrados:** toma otra fotografía desde arriba, sin cortar ninguna esquina. Usa la plantilla original y una superficie clara.
- **Respuestas erróneas:** marca los círculos completamente; revisa luz y rotación. Usa el panel de corrección manual.
- **OCR no disponible:** comprueba `tesseract --list-langs` y que `spa` y `eng` estén instalados.
- **PDF escaneado sin texto:** el OCR lo reconocerá siempre que Tesseract esté operativo; revisa el contenido y corrige errores.
- **El celular no abre la app local:** confirma la IP y Wi-Fi; revisa firewall. La foto subida es una alternativa a la cámara integrada.
- **Se perdieron las notas:** son datos de sesión, no una base de datos. Descarga el CSV antes de cerrar.

## Pruebas

```bash
python -m pytest tests -q
```

## Siguiente fase de desarrollo

Autenticación de docentes, base de datos cifrada, plantilla con identificación QR, múltiples versiones de examen, importación de matrícula, estadísticas por destreza, rúbricas para preguntas abiertas y exportación XLSX, además de una auditoría de privacidad y seguridad antes de usarlo institucionalmente.
