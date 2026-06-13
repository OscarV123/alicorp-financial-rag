import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

SIGNALS_DICT: Dict[str, Dict[str, Any]] = {
    "earnings_reports": {
        "priority": 10,
        "base_where": {"doc_type": "earnings_reports"},
        "phrase": [
            "presentacion de resultados", "informe trimestral", "reporte trimestral",
            "resultados trimestrales", "earnings release", "quarterly results",
            "1t", "2t", "3t", "4t", "primer trimestre", "segundo trimestre",
            "resultados anuales", "informe anual", "reporte anual"
        ],
        "words": {"trimestre", "trimestral", "quarter", "resultados", "ganancias", "ebitda"}
    },
    "financial_statements": {
        "priority": 30,
        "base_where": {},
        "phrase": [
            "estado de resultados", "estado de resultados integrales",
            "estado de situacion financiera", "estado de flujos de efectivo",
            "cambios en el patrimonio", "notas a los estados financieros",
            "politicas contables", "estados financieros", "eeff", "dictamen del auditor",
            "informe separado", "informe consolidado", "reporte separado", "reporte consolidado"
        ],
        "words": {
            "activos", "pasivos", "patrimonio", "ingresos", "ventas", "costo", 
            "gastos", "utilidad", "perdida", "utilidad neta", "auditor", "auditado",
            "capital", "financiero", "financieros", "balance"
        },
    },
    "important_facts": {
        "priority": 20,
        "base_where": {"doc_type": "important_facts"},
        "phrase": [
            "hecho de importancia", "hechos de importancia", "comunicacion de hecho de importancia",
            "informacion a la smv", "smv", "convocatoria a junta", "junta de accionistas",
            "emision de valores", "programa de bonos", "recompra", "redencion", "rescate"
        ],
        "words": {"hecho", "importancia", "smv", "mercado", "convocatoria", "junta", "bonos", "recompra"}
    }
}

MULTI_INTENT_MIN_PHRASE_HITS = 1

DOC_TYPE_GROUPS: Dict[str, List[str]] = {
    "earnings_reports": ["earnings_reports"],
    "important_facts": ["important_facts"],
    "financial_statements": ["eeff_separados", "eeff_consolidados"],
    "financial_statements_fallback": ["eeff_separados", "eeff_consolidados"],
    "default": [],
}

def doc_types_for_keys(keys: List[str]) -> List[str]:
    """Union (sin duplicados) de doc_type validos para una lista de keys de señal.
    Si alguna key no tiene restriccion propia (lista vacia, p.ej. 'default'),
    el resultado es [] => sin restriccion de doc_type (busqueda abierta)."""
    union: List[str] = []
    for key in keys:
        types = DOC_TYPE_GROUPS.get(key, [])
        if not types:
            return []
        for t in types:
            if t not in union:
                union.append(t)
    return union

def doc_types_for(key: str) -> List[str]:
    """Devuelve la lista de doc_type permitidos para una key de señal dada.
    Lista vacia => sin restriccion de doc_type (busqueda abierta)."""
    return DOC_TYPE_GROUPS.get(key, [])

CURRENT_YEAR = datetime.today().year 
 
MONTHS_ES = {
    "enero": "01", "ene": "01", "febrero": "02", "feb": "02", "marzo": "03", "mar": "03",
    "abril": "04", "abr": "04", "mayo": "05", "may": "05", "junio": "06", "jun": "06",
    "julio": "07", "jul": "07", "agosto": "08", "ago": "08",
    "septiembre": "09", "setiembre": "09", "sep": "09", "set": "09",
    "octubre": "10", "oct": "10", "noviembre": "11", "nov": "11", "diciembre": "12", "dic": "12"
}

@dataclass
class SignalMatch:
    key: str
    score: float
    where: Dict[str, Any]
    debug: Dict[str, Any]
 
def detect_signals(question: str) -> SignalMatch:
    question = question.lower()
    question = re.sub(r"\s+", " ", question).strip()
    
    month_detected = None
    for m, mm in MONTHS_ES.items():
        if re.search(rf"\b{re.escape(m)}\b", question):
            month_detected = mm
 
    year_match = re.search(r"\b(20\d{2})\b", question)
    year_detected = int(year_match.group(1)) if year_match else None
 
    period_detected = None
    period_match = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", question)
    if period_match:
        period_detected = period_match.group(0)
    elif month_detected and year_detected:
        period_detected = f"{year_detected}-{month_detected}"
 
    audited_intent = any(w in question for w in ["auditado", "auditados", "dictamen", "opinion del auditor", "auditor"])
    consolidado_intent = any(w in question for w in ["consolidado", "consolidados", "consolidada"])
    separado_intent = any(w in question for w in ["separado", "separados", "separada", "individual"])
 
    def phrase_hits(text: str, phrases: List[str]) -> List[str]:
        return [p for p in phrases if p in text]
    
    def words_hits_count(text: str, words: set[str]) -> int:
        tokens = set(re.findall(r"\b\w+\b", text))
        return sum(1 for w in words if w in tokens)
 
    best: Optional[SignalMatch] = None
    all_candidates: List[SignalMatch] = []
 
    for key, value in SIGNALS_DICT.items():
        priority = float(value.get("priority", 0))
        ph = phrase_hits(question, value.get("phrase", []))
        ws = words_hits_count(question, value.get("words", set()))
 
        score = 6.0 * len(ph) + 1.0 * ws + priority
        if len(ph) == 0 and ws == 0:
            continue
 
        where: Dict[str, Any] = dict(value.get("base_where", {}))
 
        if key == "financial_statements":
            if separado_intent:
                where["doc_type"] = "eeff_separados"
            elif consolidado_intent:
                where["doc_type"] = "eeff_consolidados"
            else:
                where["doc_type"] = {"$in": DOC_TYPE_GROUPS["financial_statements"]}
 
        if year_detected is not None:
            where["year"] = year_detected
        if period_detected is not None:
            where["period"] = period_detected
        if audited_intent and key == "financial_statements":
            where["audited"] = True
        
        current = SignalMatch(
            key=key, score=score, where=where,
            debug={
                "question_norm": question, "priority": priority, "phrase_hits": ph, "word_hits": ws,
                "year_for_response": year_detected, "period_detected": period_detected, 
                "audited_intent": audited_intent, "consolidado_intent": consolidado_intent, "separado_intent": separado_intent
            }
        )
        all_candidates.append(current)
 
        if best is None or current.score > best.score:
            best = current
        elif current.score == best.score:
            if len(current.debug["phrase_hits"]) > len(best.debug["phrase_hits"]):
                best = current
 
    if best is None:
        if any(w in question for w in ["capital", "patrimonio", "informe", "monto"]):
            return SignalMatch(key="financial_statements_fallback", score=10.0, 
                               where={"doc_type": {"$in": DOC_TYPE_GROUPS["financial_statements_fallback"]}}, 
                               debug={"question_norm": question, "reason": "financial_keywords_detected"})
            
        return SignalMatch(key="default", score=0.0, where={}, debug={"question_norm": question, "reason": "no_signal_matched"})
            
    multi_intent_keys = [
        c.key for c in sorted(all_candidates, key=lambda c: -c.score)
        if len(c.debug["phrase_hits"]) >= MULTI_INTENT_MIN_PHRASE_HITS
    ]
    if len(multi_intent_keys) >= 2:
        best.debug["multi_intent_keys"] = multi_intent_keys

    return best

def merge_where(match_r: SignalMatch, explicit_where: Optional[Dict[str, Any]]=None) -> SignalMatch:
    if not explicit_where:
        return match_r
    inferred = dict(match_r.where or {})
    inferred.update(explicit_where)
    return SignalMatch(key=match_r.key, score=match_r.score, where=inferred, debug=match_r.debug)
 
def relaxation_chain(where: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Genera una cadena de filtros `where`, de mas a menos restrictivo,
    soltando primero 'period', luego 'year', luego 'audited' (en ese orden).
    El primer elemento es siempre el `where` original; el ultimo es el `where`
    sin ninguna de esas tres claves (puede ser {} si no tenia otras claves)."""
    chain = [dict(where or {})]
    current = dict(where or {})
    for key_to_drop in ("period", "year", "audited"):
        if key_to_drop in current:
            current = {k: v for k, v in current.items() if k != key_to_drop}
            chain.append(dict(current))
    return chain

def build_multi_where(match_r: SignalMatch) -> Optional[Dict[str, Any]]:
    """Si detect_signals marco la pregunta como 'multi-intento' (>=2 categorias
    con match de frase exacta), construye un `where` que une los doc_type de
    todas esas categorias. Conserva 'year'/'period' si estaban presentes
    (aplican igual sin importar el doc_type), pero descarta claves especificas
    de una sola categoria (p.ej. 'audited', que no existe en doc_type=important_facts).
    Devuelve None si la pregunta no es multi-intento."""
    
    if match_r is None or not hasattr(match_r, 'debug'):
        return None

    multi_keys = match_r.debug.get("multi_intent_keys")
    if not multi_keys or len(multi_keys) < 2:
        return None
 
    union_types = doc_types_for_keys(multi_keys)
    where: Dict[str, Any] = {}
    if union_types:
        where["doc_type"] = {"$in": union_types}
 
    for shared_key in ("year", "period"):
        if shared_key in (match_r.where or {}):
            where[shared_key] = match_r.where[shared_key]
 
    return where