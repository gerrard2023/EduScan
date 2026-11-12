"""OCR de exámenes: PDF digital, PDF escaneado e imágenes."""
from io import BytesIO
import numpy as np
import cv2
import pymupdf
import pytesseract
from PIL import Image, ImageOps
from docx import Document

MAX_PAGES = 12

def _ocr_image(image: Image.Image) -> str:
    image = ImageOps.exif_transpose(image).convert('RGB')
    image.thumbnail((2800, 3600))
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    enhanced = cv2.convertScaleAbs(gray, alpha=1.12, beta=0)
    try:
        return pytesseract.image_to_string(enhanced, lang='spa+eng', config='--psm 3')
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError('No está instalado Tesseract OCR. Revisa la guía de instalación.') from exc
    except pytesseract.TesseractError as exc:
        raise RuntimeError('Tesseract requiere los idiomas español e inglés. Instala spa y eng.') from exc


def extract_text(raw: bytes, file_name: str) -> tuple[str, int]:
    if len(raw) > 15 * 1024 * 1024:
        raise ValueError('Archivo demasiado grande. Máximo: 15 MB.')
    if file_name.lower().endswith('.pdf'):
        try:
            doc = pymupdf.open(stream=raw, filetype='pdf')
        except Exception as exc:
            raise ValueError('No se pudo abrir el PDF.') from exc
        try:
            if doc.page_count > MAX_PAGES:
                raise ValueError(f'Máximo {MAX_PAGES} páginas por archivo.')
            texts = []
            for index, page in enumerate(doc):
                text = page.get_text('text', sort=True).strip()
                if len(text) < 40:
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                    image = Image.open(BytesIO(pix.tobytes('png')))
                    text = _ocr_image(image).strip()
                texts.append(f'--- PÁGINA {index+1} ---\n{text}')
            return '\n\n'.join(texts), doc.page_count
        finally:
            doc.close()
    elif file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
        try:
            return _ocr_image(Image.open(BytesIO(raw))).strip(), 1
        except OSError as exc:
            raise ValueError('La imagen no se pudo leer.') from exc
    else:
        raise ValueError('Formato incompatible: usa PDF, JPG o PNG.')


def make_docx(text: str) -> bytes:
    document = Document()
    document.add_heading('Examen digitalizado', level=1)
    document.add_paragraph('Texto reconocido por OCR. Revisar antes de reutilizar.')
    for line in text.splitlines():
        if line.strip():
            document.add_paragraph(line)
    buf = BytesIO()
    document.save(buf)
    return buf.getvalue()
