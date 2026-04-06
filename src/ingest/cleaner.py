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

def clean_text(text: str, doc_type: str = "") -> str:
    if not text:
        return ""

    doc_type = (doc_type or "").lower()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Elimina líneas muy cortas aisladas (ruido tipo símbolos, restos sueltos)
    lines = text.split("\n")
    cleaned_lines = []
    for ln in lines:
        stripped = ln.strip()

        if not stripped:
            cleaned_lines.append("")
            continue

        if len(stripped) <= 2 and not re.search(r"\d", stripped) and stripped not in {"S/", "US$", "%"}:
            continue

        cleaned_lines.append(stripped)

    text = "\n".join(cleaned_lines)

    if doc_type == "financial_statements":
        text = re.sub(r"(?m)^\s*-\s*\d+\s*-\s*$", "", text)

    if doc_type == "important_facts":
        text = re.sub(r"^[^\wáéíóúüñÁÉÍÓÚÜÑ\(]+", "", text)

    if doc_type == "earnings_reports":
        text = re.sub(r"(?m)^\s*\d+\s*$\n?", "", text, count=1)

    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()