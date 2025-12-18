"""
Limpieza y normalización del texto extraído de PDF.

Responsabilidad:
- Reducir ruido típico de PDFs (espacios, saltos extraños, encabezados repetidos).
- Mantener números y contenido financiero intacto (evitar pérdida de información).
- Entregar texto más estable para chunking y embeddings.

No hace:
- No interpreta el contenido ni lo resume.
- No asigna metadata (eso viene del loader/splitter).
"""
