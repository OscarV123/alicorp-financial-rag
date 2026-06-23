from __future__ import annotations
import bisect
import re
from pathlib import Path
import fitz
from langchain_text_splitters import MarkdownHeaderTextSplitter


PDF_BASE_DIR = Path(r"C:\Proyectos\alicorp-financial-rag\data\raw")

MIN_CHUNK_LENGTH = 30

_NO_AUDITED_TOKENS = ["noauditado", "no_auditado", "no-auditado"]

_MONTHS_ES: dict[str, str] = {
    "enero": "01",   "febrero": "02",   "marzo": "03",    "abril": "04",
    "mayo": "05",    "junio": "06",     "julio": "07",    "agosto": "08",
    "septiembre": "09", "setiembre": "09",
    "octubre": "10", "noviembre": "11", "diciembre": "12",
}

_PAGE_MARKER_RE = re.compile(r'!\[\]\(_page_(\d+)_')
_IMAGE_TAG_RE   = re.compile(r'!\[\]\([^)]+\)')


# =============================================================================
# DICCIONARIO DE CALIBRACIÓN (ANCLAS MANUALES POR DOCUMENTO)
# =============================================================================
DICCIONARIO_DE_ANCLAS: dict[str, list[tuple[str, int]]] = {
    "ReporteNoAuditado_4T-2024": [
        ("#### **1. INFORMACIÓN FINANCIERA**",                                                            4),
        ("## 1.1 ESTADO DE RESULTADOS",                                                                  4),
        ("#### **Consumo Masivo Perú**",                                                                 6),
        ("#### **Negocios Internacionales**",                                                            7),
        ("#### **B2B**",                                                                                 8),
        ("#### **Acuicultura**",                                                                         9),
        ("## 1.2. BALANCE GENERAL",                                                                     10),
        ("## 1.3. ESTADO DE FLUJO DE EFECTIVO",                                                         12),
        ("# ESTADOS FINANCIEROS CONSOLIDADOS",                                                          15),
        ("#### **Estado de resultados consolidado por los periodos terminados al 31 de diciembre",      16),
        ("# Estado de situación financiera consolidado al cierre de 31 de diciembre de 2024",           17),
        ("# DESEMPEÑO POR UNIDAD DE NEGOCIO Y REGIÓN",                                                  19),
    ],
    "Informe_Auditado_EEFF_Separados_2022": [
        ("ESTADO SEPARADO DE RESULTADOS POR",                                         7),
        ("ESTADO SEPARADO DE RESULTADOS INTEGRALES",                                  8),
        ("ESTADO SEPARADO DE SITUACI",                                                9),
        ("ESTADO SEPARADO DE CAMBIOS",                                               10),
        ("# **ALICORP S.A.A. ESTADO SEPARADO DE FLUJOS DE EFECTIVO**",              11), 
        ("# **1 INFORMACIÓN CORPORATIVA**",                                          12),
        ("# **2 BASES DE PREPARACIÓN**",                                             15),
        ("# **3 CAMBIOS EN POLÍTICAS CONTABLES Y REVELACIONES**",                    15),
        ("#### **4 JUICIOS, ESTIMADOS Y SUPUESTOS CONTABLES SIGNIFICATIVOS**",       15),
        ("# **5 INFORMACIÓN POR SEGMENTOS DE NEGOCIO**",                             17),
        ("# **6 VENTAS A TERCEROS Y A PARTES RELACIONADAS**",                        21),
        ("#### **7 COSTO DE VENTAS**",                                               21),
        ("#### **8 GASTOS DE VENTAS Y DISTRIBUCIÓN**",                               22),
        ("#### **9 GASTOS ADMINISTRATIVOS**",                                        23),
        ("# **10 OPERACIONES DISCONTINUADAS**",                                      24),
        ("#### **11 GASTOS DE PERSONAL**",                                           26),
        ("#### **12 OTROS INGRESOS Y GASTOS, NETO**",                                28),
        ("# **13 INGRESOS FINANCIEROS**",                                            30),
        ("# **14 GASTOS FINANCIEROS**",                                              31),
        ("# **15 UTILIDAD (PÉRDIDA) NETA POR ACCIÓN**",                              32),
        ("#### **16 EFECTIVO Y EQUIVALENTE DE EFECTIVO**",                           33),
        ("# **17 CUENTAS POR COBRAR COMERCIALES, NETO**",                            34),
        ("# **18 FONDO DE GARANTÍA PARA OPERACIONES CON DERIVADOS**",                38),
        ("# **19 OTRAS CUENTAS POR COBRAR, NETO**",                                  38),
        ("# **20 INVENTARIOS, NETO**",                                               41),
        ("# **21 OTROS ACTIVOS NO FINANCIEROS**",                                    43),
        ("#### **22 ACTIVOS CLASIFICADOS COMO MANTENIDOS PARA LA VENTA, NETO**",     43),
        ("# **23 INVERSIONES CONTABILIZADAS APLICANDO EL MÉTODO DE PARTICIPACION**", 45),   
        ("# **24 PROPIEDADES, PLANTA Y EQUIPO, NETO**",                              48),
        ("# **25 ACTIVOS INTANGIBLES, NETO**",                                       50),
        ("#### **26 ACTIVO POR DERECHO DE USO, NETO Y PASIVO FINANCIERO POR ARRENDAMIENTO**", 52),
        ("#### **27 PLUSVALIA**",                                                    55),
        ("# **28 OTROS PASIVOS FINANCIEROS**",                                       58),
        ("# **29 CUENTAS POR PAGAR COMERCIALES**",                                   63),
        ("# **30 OTRAS CUENTAS POR PAGAR**",                                         64),
        ("#### **31 BENEFICIOS A LOS EMPLEADOS**",                                   65),
        ("#### **32 PROVISIONES**",                                                  66),
        ("# **33 IMPUESTO A LAS GANANCIAS**",                                        67),
        ("# **34 PATRIMONIO**",                                                      67),
        ("#### **35 INSTRUMENTOS FINANCIEROS DERIVADOS**",                           67),
        ("# **36 SITUACIÓN TRIBUTARIA**",                                            68),
        ("#### **37 SALDOS Y TRANSACCIONES CON PARTES RELACIONADAS**",               68),
        ("# **38 COMPROMISOS**",                                                     68),
        ("#### **39 CONTINGENCIAS**",                                                68),
        ("# **40 OBJETIVOS Y POLÍTICAS DE GESTIÓN DEL RIESGO FINANCIERO**",          68),
        ("# **41 PRINCIPIOS Y PRACTICAS CONTABLES SIGNIFICATIVAS**",                 78),
        ("# **42 NORMAS EMITIDAS QUE TODAVÍA NO ENTRAN EN VIGOR**",                  96),
        ("# **42 EVENTOS SUBSECUENTES**",                                            97),
    ],
    "Informe_Auditado_EEFF_Consolidados_2023": [
        ("#### **ESTADO CONSOLIDADO DE RESULTADOS**",                                        8),
        ("#### **ESTADO CONSOLIDADO DE RESULTADOS INTEGRALES**",                             9),
        ("#### **ESTADO CONSOLIDADO DE SITUACIÓN FINANCIERA**",                             10),
        ("#### **ESTADO CONSOLIDADO DE CAMBIOS EN EL PATRIMONIO NETO",                     11),
        ("#### **ESTADO CONSOLIDADO DE FLUJO DE EFECTIVO**",                               12),
        ("# **4 CAMBIOS EN POLÍTICAS CONTABLES Y REVELACIONES**",                          16),
        ("### **5 JUICIOS, ESTIMADOS Y SUPUESTOS CONTABLES SIGNIFICATIVOS**",              17),
        ("#### **9 COSTO DE VENTAS**",                                                     27),
        ("# **17 UTILIDAD NETA POR ACCIÓN**",                                              32),
        ("### **44 PRINCIPIOS Y PRACTICAS CONTABLES SIGNIFICATIVAS**",                     88),
    ],
    "HechosDeImportancia_ConvocatoriaAJuntaDeAccionistas_Febrero-2023": [
        ("#### **DECLARACIÓN DE RESPONSABILIDAD**",                                          3),
        ("## **1. DATOS GENERALES**",                                                        4),
        ("## **2. OPERACIONES Y DESARROLLO**",                                              15),
        ("## **3. PROCESOS LEGALES**",                                                      41),
        ("## **4. DIRECTORIO Y GERENCIA**",                                                 41),
        ("# **RESULTADO DE LAS OPERACIONES Y SITUACIÓN ECONÓMICA FINANCIERA",              46),
        ("# **INFORMACIÓN RELATIVA A LOS VALORES DE LA SOCIEDAD",                          62),
    ],
    "HechosDeImportancia_ConvocatoriaAJuntaDeAccionistas_Febrero-2024": [
        ("# **DECLARACIÓN DE RESPONSABILIDAD**",                                              3),
        ("# **1. DATOS GENERALES**",                                                          4),
        ("# **2. OPERACIONES Y DESARROLLO**",                                                14),
        ("#### **3. PROCESOS LEGALES**",                                                     43),
        ("# **4. DIRECTORIO Y GERENCIA**",                                                   43),
        ("# **SECCIÓN III**",                                                                49),
        ("# **INFORMACIÓN RELATIVA A LOS VALORES DE LA SOCIEDAD INSCRITOS EN EL REGISTRO", 66),
    ],
    "HechosDeImportancia_EmisionDeValores_Diciembre-2023": [
        ("HECHO DE IMPORTANCIA : Comunicación de Resultado de Colocación", 1),
        ("## DATOS DE COLOCACIÓN",                                         1),
        ("## MONTO COLOCADO",                                              1),
    ],
    "HechosDeImportancia_Otros_Diciembre-2022": [
        ("## De nuestra consideración:",                                           1),
        ("## **ANEXO Adquisición de acciones comunes de propia emisión (ALICORC1)", 2),
    ],
    "HechosDeImportancia_Recompra-Redencion-Rescate_Septiembre-2024": [
        ("De nuestra consideración:", 1),
    ]
}

def obtener_anclas_por_documento(doc_id: str) -> list[tuple[str, int]]:
    """Devuelve las anclas registradas o una lista vacía si el PDF se auto-calibra bien."""
    return DICCIONARIO_DE_ANCLAS.get(doc_id, [])


def _extract_doc_metadata(md_path: Path, pdf_base_dir: Path) -> dict:
    name_doc   = md_path.stem
    name_lower = name_doc.lower()

    year_match = re.search(r"(20\d{2})", name_lower)
    year = int(year_match.group(1)) if year_match else None

    doc_type = md_path.parent.name.lower()

    if any(t in name_lower for t in _NO_AUDITED_TOKENS):
        audited = False
    elif "auditado" in name_lower:
        audited = True
    else:
        audited = False

    period: str | None = None
    for month_es, mm in _MONTHS_ES.items():
        if month_es in name_lower:
            period = f"{year}-{mm}" if year else mm
            break
    period = period or "no_definido"

    try:
        rel = md_path.relative_to(pdf_base_dir)
        source_path = (pdf_base_dir / rel).with_suffix(".pdf").as_posix()
    except ValueError:
        candidates = list(pdf_base_dir.rglob(f"{name_doc}.pdf"))
        source_path = candidates[0].as_posix() if candidates else f"data/raw/{name_doc}.pdf"

    return {
        "doc_id":      name_doc,
        "source_path": source_path,
        "year":        year,
        "doc_type":    doc_type,
        "audited":     audited,
        "period":      period,
        "source":      "Por_Definir", 
    }


def _build_offset_map(raw_text: str) -> list[int]:
    mapping: list[int] = []
    idx = 0
    n   = len(raw_text)
    while idx < n:
        if raw_text[idx:idx + 4] == "![](":
            end = raw_text.find(")", idx + 4)
            if end != -1:
                idx = end + 1
                continue
        mapping.append(idx)
        idx += 1
    return mapping


class _PageIndex:
    def __init__(
        self,
        raw_text: str,
        clean_text: str,
        offset_map: list[int],
        manual_anchors: list[tuple[str, int]],
        total_pages: int,
    ) -> None:
        self._total_pages = total_pages
        self._total_raw   = len(raw_text)

        image_anchors: list[tuple[int, int]] = []
        char_offset = 0
        for line in raw_text.splitlines():
            m = _PAGE_MARKER_RE.search(line)
            if m:
                image_anchors.append((char_offset, int(m.group(1)) + 1))
            char_offset += len(line) + 1

        manual: list[tuple[int, int]] = []
        for needle, page in manual_anchors:
            cp = clean_text.find(needle)
            if cp != -1 and cp < len(offset_map):
                manual.append((offset_map[cp], page))

        combined = sorted(set(image_anchors + manual))
        filtered: list[tuple[int, int]] = [combined[0]] if combined else []
        for char, page in combined[1:]:
            if page >= filtered[-1][1] and char > filtered[-1][0]:
                filtered.append((char, page))

        self._chars: list[int] = [a[0] for a in filtered]
        self._pages: list[int] = [a[1] for a in filtered]

    def page_at(self, raw_pos: int) -> int | None:
        if not self._chars:
            return None
        if raw_pos <= self._chars[0]:
            return self._pages[0]
        if raw_pos >= self._chars[-1]:
            if len(self._chars) < 2:
                return self._pages[-1]
            c0, p0 = self._chars[-2], self._pages[-2]
            c1, p1 = self._chars[-1], self._pages[-1]
            slope = (p1 - p0) / (c1 - c0) if c1 != c0 else 0
            return min(self._total_pages, round(p1 + slope * (raw_pos - c1)))

        idx = bisect.bisect_right(self._chars, raw_pos) - 1
        c0, p0 = self._chars[idx],     self._pages[idx]
        c1, p1 = self._chars[idx + 1], self._pages[idx + 1]
        t = (raw_pos - c0) / (c1 - c0)
        return round(p0 + t * (p1 - p0))


def _find_clean_pos_debug(
    chunk_content: str, clean_text: str, search_from: int
) -> tuple[int, bool, str]:
    """Versión debug: devuelve (posición, encontrado, método/needle usado)."""
    for line in chunk_content.splitlines():
        needle = line.strip()
        if len(needle) < 20:
            continue
        pos = clean_text.find(needle[:80], search_from)
        if pos != -1:
            return pos, True, f"line-match: {needle[:50]!r}"
    snippet = chunk_content.strip()[:80]
    pos = clean_text.find(snippet, search_from)
    if pos != -1:
        return pos, True, f"snippet-match: {snippet[:50]!r}"
    return search_from, False, "*** FALLBACK ***"


def run(md_path: Path, pdf_path: Path, output_txt_path: Path, empresa: str) -> list:
    doc_pdf = fitz.open(pdf_path)
    total_pages = doc_pdf.page_count
    doc_pdf.close()

    with open(md_path, encoding="utf-8") as f:
        raw_text = f.read()

    print("\n" + "=" * 70)
    print(f"Procesando: {pdf_path.name}")
    print(f"Empresa: {empresa} | Páginas PDF: {total_pages}")
    print("=" * 70)

    all_markers = _PAGE_MARKER_RE.findall(raw_text)

    offset_map = _build_offset_map(raw_text)
    clean_text = _IMAGE_TAG_RE.sub("", raw_text)

    doc_meta = _extract_doc_metadata(md_path, PDF_BASE_DIR)
    doc_meta["source"] = empresa

    is_hechos = "hechosdeimportancia" in doc_meta["doc_id"].lower()

    anchors_del_documento = obtener_anclas_por_documento(doc_meta["doc_id"])

    page_index = _PageIndex(raw_text, clean_text, offset_map, anchors_del_documento, total_pages)

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "seccion"), ("####", "subseccion")],
        strip_headers=False,
    )
    raw_chunks = splitter.split_text(clean_text)

    valid_chunks  = []
    search_cursor = 0
    anomalias     = []

    for raw_i, chunk in enumerate(raw_chunks):
        content = chunk.page_content.strip()
        if len(content) < MIN_CHUNK_LENGTH:
            continue

        chunk_num = len(valid_chunks) + 1
        clean_pos, found, method = _find_clean_pos_debug(content, clean_text, search_cursor)

        if clean_pos >= search_cursor:
            search_cursor = clean_pos + len(content)

        safe_clean_pos = min(clean_pos, len(offset_map) - 1)
        raw_pos = offset_map[safe_clean_pos]

        page_number = page_index.page_at(raw_pos) or 1
        page_number = min(total_pages, page_number)

        anchor_applied = None
        for needle, manual_page in anchors_del_documento:
            if needle in content:
                page_number = min(total_pages, manual_page)
                anchor_applied = needle[:40]
                break

        is_anomaly = False
        reasons    = []

        if page_number == 1 and chunk_num > 1 and not anchor_applied:
            is_anomaly = True
            if not all_markers and not anchors_del_documento:
                reasons.append("sin marcadores ni anclas manuales")
            elif not all_markers:
                reasons.append("sin marcadores — interpolando solo desde anclas manuales")
            elif not found:
                reasons.append("FALLBACK: texto no hallado en clean_text")
            else:
                reasons.append("chunk antes del primer ancla conocida")

        if not found:
            is_anomaly = True
            reasons.append(f"FALLBACK activo (cursor={search_cursor})")

        if is_anomaly:
            anomalias.append({
                "chunk_num": chunk_num,
                "raw_i":     raw_i,
                "seccion":   chunk.metadata.get("seccion", "")[:60],
                "preview":   content[:80].replace("\n", " "),
                "clean_pos": clean_pos,
                "raw_pos":   raw_pos,
                "page_num":  page_number,
                "reasons":   reasons,
                "method":    method,
            })

        chunk.metadata     = {**doc_meta, "page_number": page_number, **chunk.metadata}
        chunk.page_content = content
        valid_chunks.append(chunk)

    paginas_1 = sum(1 for c in valid_chunks if c.metadata["page_number"] == 1)
    print(f"[RES] Chunks válidos: {len(valid_chunks)} | page=1: {paginas_1} | anomalías: {len(anomalias)}")

    if is_hechos and anomalias:
        print(f"\n{'─'*70}")
        print(f"ANOMALÍAS DETECTADAS ({len(anomalias)}):")
        print(f"{'─'*70}")
        for a in anomalias:
            print(f"\n  Chunk {a['chunk_num']:>4} (raw #{a['raw_i']}) → page={a['page_num']}")
            print(f"  Sección : {a['seccion']!r}")
            print(f"  Preview : {a['preview']!r}")
            print(f"  Causas  : {' | '.join(a['reasons'])}")
            print(f"  Detalle : clean_pos={a['clean_pos']} raw_pos={a['raw_pos']:,} método={a['method']}")
    elif is_hechos:
        print("[OK] Sin anomalías detectadas.")

    output_txt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_txt_path, "w", encoding="utf-8") as out:
        out.write(f"Total chunks válidos: {len(valid_chunks)}\n\n")
        for i, chunk in enumerate(valid_chunks):
            out.write(f"{'=' * 70}\n")
            out.write(f"CHUNK {i + 1}\n")
            out.write(f"Metadata: {chunk.metadata}\n")
            out.write(f"{'=' * 70}\n")
            out.write(chunk.page_content)
            out.write("\n\n")

    print(f"\nChunks originales : {len(raw_chunks)}")
    print(f"Chunks válidos    : {len(valid_chunks)}")
    print(f"Exportado txt a   : {output_txt_path}")

    return valid_chunks