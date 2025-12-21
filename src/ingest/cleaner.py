# ===================================================================================l
# Limpieza y normalización del texto extraído de PDF.                                |       
#                                                                                    |
# Responsabilidad:                                                                   |
# - Reducir ruido típico de PDFs (espacios, saltos extraños, encabezados repetidos). |
# - Mantener números y contenido financiero intacto (evitar pérdida de información). |
# - Entregar texto más estable para chunking y embeddings.                           |
#                                                                                    |
# No hace:                                                                           |
# - No interpreta el contenido ni lo resume.                                         | 
# - No asigna metadata (eso viene del loader).                                       |
# ===================================================================================|
import re

def clean_text(text: str) -> str:
    if not text:
        return ""
    
    # Clearning rules
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"(?<=\w)\s*\n\s*(?=\w)", " ", text)
    text = re.sub(r"([A-Za-zÁÉÍÓÚÜÑáéíóúüñ])\n([A-Za-zÁÉÍÓÚÜÑáéíóúüñ])", r"\1 \2", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    
    return text.strip()