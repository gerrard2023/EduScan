"""Lectura OMR de la plantilla fija EduScan v1. No usar con formularios arbitrarios."""
from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

PAGE_W, PAGE_H = 1200, 1700
MARKER_CENTERS = np.float32([(85, 85), (1115, 85), (85, 1615), (1115, 1615)])
ALLOWED_COUNTS = (5, 10, 15, 20)
OPTIONS = "ABCD"
BUBBLE_X = (470, 630, 790, 950)
FIRST_Y = 400
ROW_STEP = 47
BUBBLE_RADIUS = 18

class OMRException(ValueError):
    """Error recuperable para imágenes que no cumplen con la plantilla."""


def circles(n_questions: int):
    if n_questions not in ALLOWED_COUNTS:
        raise ValueError("Número de preguntas inválido")
    return [[(BUBBLE_X[j], FIRST_Y + i * ROW_STEP) for j in range(4)]
            for i in range(n_questions)]


def read_image(raw: bytes) -> np.ndarray:
    """Decodifica, respetando la orientación EXIF del teléfono."""
    from PIL import ImageOps
    with Image.open(BytesIO(raw)) as photo:
        photo = ImageOps.exif_transpose(photo).convert('RGB')
        # evita imágenes enormes en teléfonos
        photo.thumbnail((3000, 4000))
        return cv2.cvtColor(np.array(photo), cv2.COLOR_RGB2BGR)


def _find_markers(img: np.ndarray):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape
    # Otsu deja fuera la textura clara y conserva recuadros negros
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    found, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    possible = []
    total = W * H
    for contour in found:
        area = cv2.contourArea(contour)
        if not 0.00024 * total < area < 0.012 * total:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        ratio = w / max(h, 1)
        if not 0.67 < ratio < 1.48:
            continue
        if area / max(w * h, 1) < 0.57:
            continue
        # solo marcadores cercanos a esquinas de la foto
        cx, cy = x + w / 2, y + h / 2
        nx, ny = cx / W, cy / H
        if not ((nx < 0.34 or nx > 0.66) and (ny < 0.27 or ny > 0.73)):
            continue
        possible.append((cx, cy, area))
    if len(possible) < 4:
        raise OMRException("No se reconocieron los cuatro cuadros negros. Fotografía la hoja completa, recta y con buena luz.")

    # Seleccionamos los candidatos más externos, pero con un único marcador por esquina.
    corners = ((0.05, 0.05), (0.95, 0.05), (0.05, 0.95), (0.95, 0.95))
    chosen = []
    for x0, y0 in corners:
        subset = [(cx, cy, ar) for cx, cy, ar in possible
                  if (cx / W < 0.5) == (x0 < 0.5)
                  and (cy / H < 0.5) == (y0 < 0.5)]
        if not subset:
            raise OMRException("No se identificaron las cuatro esquinas de la plantilla. Ajusta la orientación y vuelve a tomar la foto.")
        # favorece los cuadrados con tamaño similar a los otros marcadores y la posición esperada
        subset.sort(key=lambda r: (((r[0] / W - x0) ** 2 + (r[1] / H - y0) ** 2) ** 0.5))
        chosen.append(subset[0][:2])
    return np.float32(chosen)


def deskew(img: np.ndarray) -> np.ndarray:
    corners = _find_markers(img)
    mat = cv2.getPerspectiveTransform(corners, MARKER_CENTERS)
    return cv2.warpPerspective(img, mat, (PAGE_W, PAGE_H), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))


def _bubble_fill(binary: np.ndarray, x: int, y: int) -> float:
    # Interior del círculo, sin tocar el borde impreso.
    r = 12
    patch = binary[y - r:y + r + 1, x - r:x + r + 1]
    if patch.shape != (2*r+1, 2*r+1):
        return 0.0
    yy, xx = np.ogrid[-r:r+1, -r:r+1]
    mask = xx*xx + yy*yy <= r*r
    return float(np.count_nonzero(patch[mask])) / float(np.count_nonzero(mask))


def analyze(raw: bytes, n_questions: int, rotation: int = 0) -> dict:
    if n_questions not in ALLOWED_COUNTS:
        raise OMRException("La plantilla permite 5, 10, 15 o 20 preguntas")
    img = read_image(raw)
    if rotation not in (0, 90, 180, 270):
        raise OMRException("Rotación inválida")
    rotation_code = {90: cv2.ROTATE_90_CLOCKWISE,
                     180: cv2.ROTATE_180,
                     270: cv2.ROTATE_90_COUNTERCLOCKWISE}
    if rotation:
        img = cv2.rotate(img, rotation_code[rotation])
    corrected = deskew(img)
    gray = cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    thresholded = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY_INV, 41, 12)
    results = []
    annotated = corrected.copy()
    for idx, row in enumerate(circles(n_questions), start=1):
        values = [_bubble_fill(thresholded, x, y) for x, y in row]
        selected = [j for j, v in enumerate(values) if v >= 0.28]
        if len(selected) == 1:
            answer = OPTIONS[selected[0]]
            state = "Detectada"
        elif len(selected) > 1:
            answer = ""
            state = "Marca múltiple"
        else:
            answer = ""
            state = "En blanco o marca tenue"
        results.append({'pregunta': idx, 'respuesta': answer, 'estado': state,
                        'intensidades': [round(v, 2) for v in values]})
        for j, (x, y) in enumerate(row):
            col = (30, 160, 30) if (len(selected) == 1 and selected[0] == j) else (0, 120, 255) if j in selected else (180, 180, 180)
            cv2.circle(annotated, (x, y), 24, col, 2)
    ok, encoded = cv2.imencode('.png', annotated)
    if not ok:
        raise OMRException("No se pudo generar la vista de revisión")
    return {'resultados': results, 'imagen': encoded.tobytes(), 'ambiguas': sum(r['estado'] != 'Detectada' for r in results)}
