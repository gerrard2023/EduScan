"""PDF A4 imprimible con casillas y marcadores de posición OMR."""
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from omr import PAGE_W, PAGE_H, MARKER_CENTERS, BUBBLE_X, FIRST_Y, ROW_STEP, BUBBLE_RADIUS, ALLOWED_COUNTS


def generate_sheet(count: int, title: str = 'EDUSCAN - HOJA DE RESPUESTAS') -> bytes:
    if count not in ALLOWED_COUNTS:
        raise ValueError("Elige 5, 10, 15 o 20 preguntas")
    output = BytesIO()
    paper_w, paper_h = A4
    sx, sy = paper_w / PAGE_W, paper_h / PAGE_H
    pdf = canvas.Canvas(output, pagesize=A4)
    pdf.setTitle('EduScan - hoja de respuestas OMR')
    def rect(x, y, w, h, fill=0, stroke=1):
        pdf.rect(x*sx, paper_h - (y+h)*sy, w*sx, h*sy, fill=fill, stroke=stroke)
    def txt(x, y, message, size=11, bold=False):
        pdf.setFont('Helvetica-Bold' if bold else 'Helvetica', size)
        pdf.drawString(x*sx, paper_h-y*sy, message)
    def circle(x, y, radius):
        pdf.circle(x*sx, paper_h-y*sy, radius*sx, stroke=1, fill=0)

    # Fiduciales sólidos; deben permanecer completos en la fotografía.
    pdf.setFillColorRGB(0, 0, 0)
    for x,y in MARKER_CENTERS:
        rect(x-28, y-28, 56, 56, fill=1, stroke=0)
    txt(168, 111, title[:48], 16, True)
    txt(170, 161, 'Nombre / código: _________________________________________', 11)
    txt(170, 200, 'Curso / paralelo: __________________________________________', 11)
    txt(170, 239, 'Fecha: __________________    Asignatura: ____________________', 10)
    txt(165, 300, 'Marque una sola respuesta por pregunta. Rellene el círculo completamente.', 9)
    txt(165, 321, 'No doble la hoja ni cubra los cuatro cuadros negros.', 9)
    pdf.setStrokeColorRGB(0.2,0.2,0.2)
    txt(194, 368, 'PREGUNTA', 10, True)
    for j, label in enumerate('ABCD'):
        txt(BUBBLE_X[j]-8, 368, label, 11, True)
    for i in range(count):
        y = FIRST_Y + i * ROW_STEP
        txt(210, y + 5, f'{i+1:02d}', 11, True)
        for x in BUBBLE_X:
            pdf.setLineWidth(1.25)
            circle(x, y, BUBBLE_RADIUS)
    bottom = FIRST_Y + count * ROW_STEP + 75
    txt(165, bottom, 'Las respuestas poco claras deben revisarse por el docente.', 9)
    txt(165, 1533, 'Plantilla EduScan v1 | A4 | Imprimir al 100% (sin ajustar escala)', 8)
    pdf.showPage()
    pdf.save()
    return output.getvalue()
