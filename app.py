"""EduScan v1 - Aplicación web para OCR y lectura OMR de hojas estandarizadas."""
from __future__ import annotations
from datetime import datetime
from hashlib import sha256
from io import BytesIO

import pandas as pd
import streamlit as st

from plantilla import generate_sheet
from omr import analyze, OMRException, ALLOWED_COUNTS
from digitalizador import extract_text, make_docx

st.set_page_config(page_title='EduScan | Exámenes digitales', page_icon='📄',
                   layout='wide', initial_sidebar_state='expanded')
st.markdown('''<style>
.block-container{max-width:1150px;padding-top:1.6rem}
.hero{border:1px solid #dce8ec;border-radius:18px;padding:22px 26px;
background:linear-gradient(115deg,#eef7f9 0%,#fff 85%);margin-bottom:15px}
.hero h1{color:#10576c;margin:0;font-size:2.0rem}
.hero p{color:#476471;margin:6px 0 0;font-size:1.03rem}
.smallnote{color:#5d7180;font-size:.89rem}
[data-testid="stMetric"]{border:1px solid #e1e9ed;border-radius:12px;padding:12px;background:white}
</style>''', unsafe_allow_html=True)

st.markdown('''<div class="hero"><h1>EduScan</h1>
<p>Digitaliza exámenes, imprime hojas de respuestas y califica evaluaciones de opción múltiple.</p></div>''',
unsafe_allow_html=True)

with st.sidebar:
    st.header('EduScan v1.0')
    st.write('**Flujo recomendado**')
    st.write('1. Crea la clave de respuestas.\n\n2. Imprime las hojas A4 al 100%.\n\n3. Pide a los estudiantes rellenar los círculos.\n\n4. Fotografía cada hoja y revisa la nota.\n\n5. Descarga el registro CSV.')
    st.divider()
    st.info('La aplicación no guarda archivos ni notas en una base de datos. Los resultados permanecen temporalmente en esta sesión del navegador.')
    st.caption('Prototipo docente. Antes de un uso institucional, implementar acceso autenticado, controles de seguridad y protección de datos.')

if 'historial' not in st.session_state:
    st.session_state.historial = []
if 'ocr_text' not in st.session_state:
    st.session_state.ocr_text = ''

ocr_tab, template_tab, scan_tab, history_tab = st.tabs([
    '1. Digitalizar examen', '2. Hoja y clave', '3. Calificar', '4. Resultados'])

with ocr_tab:
    st.subheader('Convertir fotografías o PDF en texto editable')
    st.write('Admite exámenes con texto impreso en español e inglés. En PDF digitales aprovecha el texto existente; en imágenes y PDF escaneados utiliza OCR.')
    upload = st.file_uploader('Carga un examen PDF, JPG o PNG', type=['pdf','jpg','jpeg','png'], key='ocr_upload')
    camera = st.camera_input('O toma una fotografía del examen', key='ocr_camera')
    selected = upload or camera
    if selected:
        st.caption(f'Archivo seleccionado: {selected.name} ({selected.size / 1024:.0f} KB)')
    if st.button('Reconocer texto', disabled=not bool(selected), type='primary', key='ocr_button'):
        try:
            with st.spinner('Reconociendo páginas...'):
                content, total = extract_text(selected.getvalue(), selected.name)
            st.session_state['ocr_text'] = content
            st.success(f'Procesamiento finalizado: {total} página(s). Revisa el texto antes de utilizarlo.')
        except (ValueError, RuntimeError, Exception) as exc:
            st.error(f'No se pudo digitalizar: {exc}')
    text = st.text_area('Texto reconocido (puedes corregirlo aquí)', height=320, key='ocr_text',
                        placeholder='Aquí aparecerá el examen digitalizado.')
    if text.strip():
        c1, c2 = st.columns(2)
        with c1:
            st.download_button('Descargar Word editable', data=make_docx(text), file_name='examen_digitalizado.docx',
                               mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document', use_container_width=True)
        with c2:
            st.download_button('Descargar texto TXT', data=text.encode('utf-8-sig'), file_name='examen_digitalizado.txt',
                               mime='text/plain', use_container_width=True)
    st.caption('El OCR no garantiza conservar tablas, gráficos, ecuaciones ni el formato original. Verifica nombres, preguntas y puntuación.')

with template_tab:
    st.subheader('Crear hoja de respuestas y clave de corrección')
    col_a, col_b = st.columns([1, 2])
    with col_a:
        count = st.selectbox('Número de preguntas', options=ALLOWED_COUNTS, index=1, key='count')
        subject = st.text_input('Asignatura (opcional)', value='Inglés', max_chars=50)
        exam_title = st.text_input('Título del examen (opcional)', value='Evaluación', max_chars=50)
    with col_b:
        st.info('La clave se mantiene en esta sesión. Completa cada respuesta correcta antes de calificar.')
        st.caption('El sistema acepta cuatro alternativas por pregunta: A, B, C y D. Cada acierto tiene el mismo peso.')
    st.markdown('**Clave de respuestas correctas**')
    answers = []
    for row_start in range(0, count, 5):
        columns = st.columns(5)
        for offset, col in enumerate(columns):
            idx = row_start + offset
            if idx < count:
                with col:
                    answers.append(st.selectbox(f'Pregunta {idx+1}', options=['A', 'B', 'C', 'D'],
                                                 key=f'key_{idx}', index=0))
    pdf = generate_sheet(count)
    st.download_button('Descargar hoja de respuestas A4 (PDF)', data=pdf,
                       file_name=f'hoja_respuestas_{count}p.pdf', mime='application/pdf',
                       type='primary', use_container_width=True)
    st.caption('Imprime en tamaño A4, escala real (100%), sin recortes ni ajustes automáticos. No cambies el diseño de la hoja.')

with scan_tab:
    st.subheader('Calificar una hoja de respuestas')
    st.write(f'Examen actual: **{exam_title}** - {subject} - **{count} preguntas**.')
    st.caption('La lectura requiere la hoja EduScan descargada en la pestaña anterior, no una hoja arbitraria.')
    left, right = st.columns(2)
    with left:
        student = st.text_input('Estudiante o código (opcional)', placeholder='Ej.: Estudiante 001')
    with right:
        group = st.text_input('Curso y paralelo (opcional)', placeholder='Ej.: 9.° EGB D')
    method = st.radio('Origen de la hoja resuelta', ['Subir imagen', 'Tomar fotografía'], horizontal=True)
    if method == 'Subir imagen':
        photo = st.file_uploader('Selecciona la foto JPG o PNG', type=['jpg','jpeg','png'], key='omr_upload')
    else:
        photo = st.camera_input('Fotografía la hoja completa, con las cuatro esquinas visibles', key='omr_cam')
    rotation = st.selectbox('Girar imagen si es necesario', [0, 90, 180, 270],
                            format_func=lambda x: f'{x}°', help='Ángulo horario. La hoja debe verse vertical y con el encabezado arriba.')
    current_digest = sha256(photo.getvalue()).hexdigest() if photo else None
    if st.button('Detectar respuestas y calcular nota', type='primary', disabled=not bool(photo), key='scan_button'):
        try:
            if photo.size > 15 * 1024 * 1024:
                raise OMRException('La imagen supera los 15 MB permitidos.')
            with st.spinner('Alineando la hoja y leyendo círculos...'):
                data = analyze(photo.getvalue(), count, rotation)
            data['count'] = count
            data['digest'] = current_digest
            data['rotation'] = rotation
            st.session_state.last_scan = data
            st.success('Hoja analizada. Confirma las respuestas antes de guardar el resultado.')
        except (OMRException, ValueError) as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f'No fue posible analizar la hoja. Prueba otra fotografía. Detalle: {exc}')

    scan = st.session_state.get('last_scan')
    if scan:
        if scan['count'] != count or (photo and scan['digest'] != current_digest) or scan['rotation'] != rotation:
            st.warning('La plantilla, la imagen o la rotación cambiaron. Ejecuta de nuevo el análisis para actualizar el resultado.')
        else:
            img_col, result_col = st.columns([1, 1])
            with img_col:
                st.image(scan['imagen'], caption='Imagen alineada. Verde: opción detectada; naranja: revisar marcas.',
                         use_container_width=True)
                st.download_button('Descargar imagen revisada', scan['imagen'], file_name='revision_omr.png',
                                   mime='image/png', use_container_width=True)
            with result_col:
                detected = scan['resultados']
                if scan['ambiguas']:
                    st.warning(f"{scan['ambiguas']} pregunta(s) requieren revisión por estar en blanco o tener varias marcas.")
                else:
                    st.success('Todas las preguntas presentan una marca reconocible.')
                st.markdown('**Corregir detecciones manualmente**')
                st.caption('Selecciona una opción cuando la foto no se leyó bien. Deja "Sin respuesta" para un blanco real.')
                review = []
                with st.expander('Ver o corregir respuestas', expanded=bool(scan['ambiguas'])):
                    for r in detected:
                        initial = r['respuesta'] or 'Sin respuesta'
                        chosen = st.selectbox(f"{r['pregunta']}. {r['estado']}",
                                              ['Sin respuesta', 'A', 'B', 'C', 'D'],
                                              index=['Sin respuesta', 'A', 'B', 'C', 'D'].index(initial),
                                              key=f"edit_{scan['digest'][:12]}_{scan['count']}_{r['pregunta']}")
                        review.append('' if chosen == 'Sin respuesta' else chosen)
                # El valor del widget se conserva aunque el expander esté contraído.
                if not review:
                    review = [r['respuesta'] for r in detected]
                correct = sum(a == b for a, b in zip(review, answers))
                grade = round(correct * 10 / count, 2)
                st.metric('Calificación / 10', f'{grade:.2f}', delta=f'{correct} aciertos de {count}', delta_color='off')
                summary = pd.DataFrame([{
                    'Pregunta': i+1, 'Clave': answers[i], 'Leída / revisada': review[i] or '—',
                    'Resultado': 'Correcta' if review[i] == answers[i] else 'Incorrecta / blanco'}
                    for i in range(count)])
                st.dataframe(summary, hide_index=True, use_container_width=True)
                if st.button('Agregar calificación al registro de la sesión', type='primary', use_container_width=True):
                    label = student.strip()[:90] if student.strip() else 'Sin identificar'
                    st.session_state.historial.append({
                        'Fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'Estudiante': label, 'Curso': group.strip()[:60],
                        'Examen': exam_title[:50], 'Asignatura': subject[:50],
                        'Preguntas': count, 'Aciertos': correct, 'Nota_10': grade,
                        'Respuestas': ','.join(s or '-' for s in review)})
                    st.success('Calificación incorporada al registro temporal. Descarga el archivo CSV antes de cerrar la sesión.')

with history_tab:
    st.subheader('Registro de calificaciones')
    if not st.session_state.historial:
        st.info('Todavía no hay resultados. Califica una hoja y agrégala al registro.')
    else:
        history_df = pd.DataFrame(st.session_state.historial)
        c1, c2, c3 = st.columns(3)
        c1.metric('Registros', len(history_df))
        c2.metric('Promedio / 10', f"{history_df['Nota_10'].mean():.2f}")
        c3.metric('Notas de 7 o más', int((history_df['Nota_10'] >= 7).sum()))
        st.dataframe(history_df, use_container_width=True, hide_index=True)
        st.download_button('Descargar calificaciones CSV (Excel)',
                           history_df.to_csv(index=False).encode('utf-8-sig'),
                           file_name='calificaciones_eduscan.csv', mime='text/csv',
                           type='primary', use_container_width=True)
        if st.button('Borrar registro temporal'):
            st.session_state.historial = []
            st.rerun()
    st.caption('Los datos no se guardan al cerrar la sesión. CSV puede abrirse con Excel. Antes de publicar para uso real, proteger el acceso y las notas.')
