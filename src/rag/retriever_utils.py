import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

SIGNALS_DICT: Dict[str, Dict[str, Any]] = {
    "earnings_reports": {
        "priority": 10,
        "base_where": {"doc_type": "earnings_reports"},
        "phrase": [
            "presentacion de resultados",
            "informe trimestral",
            "reporte trimestral",
            "resultados trimestrales",
            "earnings release",
            "quarterly results",
            "trading update",
            "1t", "2t", "3t", "4t",
            "primer trimestre", "segundo trimestre", "tercer trimestre", "cuarto trimestre",
            "q1", "q2", "q3", "q4",
            "first quarter", "second quarter", "third quarter", "fourth quarter",
            "6m", "semestral", "primer semestre", "segundo semestre", "half year",
            "9m", "nueve meses", "nine months",
            "12m", "doce meses", "twelve months", "full year",
            "resultados anuales", "informe anual", "reporte anual",
        ],
        "words": {
            "trimestre", "trimestral", "quarter",
            "resultados", "ganancias", "earnings",
            "ingresos", "ventas", "volumen", "precio", "mix",
            "margen", "bruto", "operativo", "neto",
            "ebitda", "ajustado", "adjusted",
            "capex", "inversion",
            "flujo", "caja", "cash", "cashflow",
            "deuda", "apalancamiento", "leverage",
            "guidance", "outlook", "proyecciones", "estimaciones",
            "crecimiento", "yoy", "qoq",
            "consolidado", "consolidados",
        },
        "period_signals": {
            "Q1": {
                "triggers": ["1t", "q1", "primer trimestre", "first quarter"],
                "months": ["01", "02", "03"]
            },
            "Q2": {
                "triggers": ["2t", "q2", "segundo trimestre", "second quarter"],
                "months": ["04", "05", "06"]
            },
            "Q3": {
                "triggers": ["3t", "q3", "tercer trimestre", "third quarter"],
                "months": ["07", "08", "09"]
            },
            "Q4": {
                "triggers": ["4t", "q4", "cuarto trimestre", "fourth quarter"],
                "months": ["10", "11", "12"]
            },
            "6M": {
                "triggers": ["6m", "semestral", "half year"],
                "months": ["01", "02", "03", "04", "05", "06"]
            },
            "H1": {
                "triggers": ["primer semestre", "first half", "h1"],
                "months": ["01", "02", "03", "04", "05", "06"]
            },
            "H2": {
                "triggers": ["segundo semestre", "second half", "h2"],
                "months": ["07", "08", "09", "10", "11", "12"]
            },
            "9M": {
                "triggers": ["9m", "nueve meses", "nine months"],
                "months": ["01", "02", "03", "04", "05", "06", "07", "08", "09"]
            },
            "12M": {
                "triggers": ["12m", "doce meses", "twelve months", "full year", "resultados anuales", "informe anual", "reporte anual", "fy"],
                "months": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
            }
        }
    },
    "financial_statements": {
        "priority": 30,
        "base_where": {"doc_type": "financial_statements"},
        "phrase": [
            "estado de resultados",
            "estado de resultados integrales",
            "estado de situacion financiera",
            "estado de flujos de efectivo",
            "cambios en el patrimonio",
            "notas a los estados financieros",
            "politicas contables",
            "estados financieros",
            "eeff",
            "dictamen del auditor",
        ],
        "words": {
            "activos", "pasivos", "patrimonio",
            "ingresos", "ventas", "costo", "costos",
            "gastos", "utilidad", "perdida",
            "utilidad neta", "resultado neto",
            "flujo", "efectivo", "equivalentes",
            "depreciacion", "deterioro", "impuesto",
            "auditor", "auditado", "dictamen",
        },
    },
    "important_facts": {
        "priority": 20,
        "base_where": {"doc_type": "important_facts"},
        "phrase": [
            "hecho de importancia", "hechos de importancia",
            "comunicacion de hecho de importancia",
            "informacion a la smv",
            "superintendencia del mercado de valores",
            "smv", "comunicado al mercado",
            "convocatoria a junta", "convocatoria a junta general",
            "junta general de accionistas", "junta de accionistas",
            "asamblea de accionistas", "sesion de directorio",
            "acuerdos de junta", "acuerdo de junta",
            "agenda de la junta", "orden del dia",
            "quorum", "poderes para la junta", "otorgamiento de poderes",
            "emision de valores", "programa de bonos",
            "programa de instrumentos", "bonos corporativos",
            "papeles comerciales", "instrumentos de deuda",
            "oferta publica", "colocacion",
            "prospecto", "registro de valores",
            "inscripcion en el registro",
            "tasa de interes", "plazo de vencimiento",
            "condiciones de la emision",
            "recompra", "programa de recompra",
            "recompra de acciones", "adquisicion de acciones propias",
            "redencion", "rescate",
            "cancelacion anticipada", "amortizacion",
            "rescate anticipado", "call option",
        ],
        "words": {
            "hecho", "importancia", "smv", "mercado", "comunicado", "relevante",
            "convocatoria", "junta", "accionistas", "asamblea", "directorio",
            "sesion", "acuerdo", "agenda", "quorum",
            "votacion", "delegacion",
            "emision", "valores", "bonos", "deuda", "instrumentos",
            "papeles", "prospecto", "registro", "oferta",
            "colocacion", "tasa", "interes", "vencimiento",
            "recompra", "redencion", "rescate", "amortizacion",
            "cancelacion", "anticipada",
        },
        "topic_signals": {
            "junta_convocatoria": [
                "convocatoria", "junta", "accionistas", "asamblea", "agenda", "orden del dia"
            ],
            "emision_valores": [
                "emision", "valores", "bonos", "papeles comerciales", "prospecto", "colocacion"
            ],
            "recompra_redencion_rescate": [
                "recompra", "redencion", "rescate", "amortizacion", "cancelacion anticipada"
            ],
            "otros": ["evento", "relevante", "comunicado"],
        },
    },
}

CURRENT_YEAR = datetime.now().year

MONTHS_ES = {
    "enero": "01", "ene": "01",
    "febrero": "02", "feb": "02",
    "marzo": "03", "mar": "03",
    "abril": "04", "abr": "04",
    "mayo": "05", "may": "05",
    "junio": "06", "jun": "06",
    "julio": "07", "jul": "07",
    "agosto": "08", "ago": "08",
    "septiembre": "09", "setiembre": "09", "sep": "09", "set": "09",
    "octubre": "10", "oct": "10",
    "noviembre": "11", "nov": "11",
    "diciembre": "12", "dic": "12",
}

RELATIVE_YEAR_RULES = [
    {"offset": 0,  "type": "phrase", "patterns": [
        "este año", "este anio",
        "del presente año", "del presente anio",
        "en el presente año", "en el presente anio",
        "año en curso", "anio en curso",
    ]},
    {"offset": -1, "type": "phrase", "patterns": [
        "el año pasado", "el anio pasado",
        "año pasado", "anio pasado",
        "el año anterior", "el anio anterior",
        "año anterior", "anio anterior",
        "del año pasado", "del anio pasado",
    ]},
    {"offset": +1, "type": "phrase", "patterns": [
        "el próximo año", "el proximo anio",
        "próximo año", "proximo anio",
        "año que viene", "anio que viene",
        "el año que viene", "el anio que viene",
        "el siguiente año", "el siguiente anio",
    ]},

    {"type": "regex", "kind": "past", "pattern": r"\bhace\s+(\d{1,2})\s+a(?:ñ|n)os?\b"},
    {"type": "regex", "kind": "past", "pattern": r"\b(\d{1,2})\s+a(?:ñ|n)os?\s+atr[aá]s\b"},
    {"type": "regex", "kind": "future", "pattern": r"\ben\s+(\d{1,2})\s+a(?:ñ|n)os?\b"},
]


@dataclass
class SignalMatch:
    key: str
    score: float
    where: Dict[str, Any]
    debug: Dict[str, Any]

def detect_relative_year(text: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    for rule in RELATIVE_YEAR_RULES:
        if rule.get("type") == "phrase":
            
            for p in rule["patterns"]:
                if p in text:
                    return (CURRENT_YEAR + int(rule["offset"]), "relative_phrase", p)
                    
    for rule in RELATIVE_YEAR_RULES:
        if rule.get("type") == "regex":
            
            m = re.search(rule["pattern"], text)
            if not m:
                continue
            
            n = int(m.group(1))
            if rule["kind"] == "past":
                return (CURRENT_YEAR - n, "relative_regex_past", m.group(0))
            if rule["kind"] == "future":
                return (CURRENT_YEAR + n, "relative_regex_future", m.group(0))
    
    return (None, None, None)

def detect_signals(question: str) -> SignalMatch:
    question = question.lower()
    question = re.sub(r"\s+", " ", question).strip()
    
    month_detected: Optional[str] = None
    month_detected_token: Optional[str] = None

    for m, mm in MONTHS_ES.items():
        if re.search(rf"\b{re.escape(m)}\b", question):
            if month_detected_token is None or len(m) > len(month_detected_token):
                month_detected_token = m
                month_detected = mm

    year_source: Optional[str] = None
    year_trigger: Optional[str] = None
        
    year_match = re.search(r"\b(20\d{2})\b", question)
    year_detected: Optional[int] =int(year_match.group(1)) if year_match else None

    if year_detected is not None:
        year_source = "explicit"
        year_trigger = year_match.group(0)
    else:
        y, src, trg = detect_relative_year(question)
        if y is not None:
            year_detected = y
            year_source = src
            year_trigger = trg

    period_match = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", question)
    period_detected = period_match.group(0) if period_match else None

    if period_detected is None and month_detected and year_detected:
        period_detected = f"{year_detected}-{month_detected}"

    audited_intent = any(w in question for w in ["auditado", "auditados", "dictamen", "opinion del auditor", "auditor"])

    def phrase_hits(text: str, phrases: List[str]) -> List[str]:
        return [p for p in phrases if p in text]
    
    def words_hits_count(text: str, words: set[str]) -> int:
        tokens = set(re.findall(r"\b\w+\b", text))
        return sum(1 for w in words if w in tokens)

    best: Optional[SignalMatch] = None

    for key, value in SIGNALS_DICT.items():
        priority = float(value.get("priority", 0))

        ph = phrase_hits(question, value.get("phrase", []))
        ws = words_hits_count(question, value.get("words", set()))

        score = 6.0 * len(ph) + 1.0 * ws + priority

        if len(ph) == 0 and ws == 0:
            continue

        where: Dict[str, Any] = dict(value.get("base_where", {}))

        if year_detected is not None:
            where["year"] = year_detected

        if period_detected is not None:
            where["period"] = period_detected

        if audited_intent and where.get("doc_type") == "financial_statements":
            where["audited"] = True
        
        current = SignalMatch(
            key=key,
            score=score,
            where=where,
            debug={
                "question_norm": question,
                "priority": priority,
                "phrase_hits": ph,
                "word_hits": ws,
                "year_for_response": year_detected,
                "year_source": year_source,
                "year_trigger": year_trigger,
                "current_year_runtime": CURRENT_YEAR,
                "month_detected": month_detected,
                "period_detected": period_detected,
                "audited_intent": audited_intent
            }
        )

        if best is None:
            best = current
        else:
            if current.score > best.score:
                best = current
            elif current.score == best.score:
                if len(current.debug["phrase_hits"]) > len(best.debug["phrase_hits"]):
                    best = current
                elif len(current.debug["phrase_hits"]) == len (best.debug["phrase_hits"]):
                    if current.debug["priority"] > best.debug["priority"]:
                        best = current

    if best is None:
        return SignalMatch(
            key="default",
            score=0.0,
            where={},
            debug={
                "question_norm": question,
                "reason": "no_signal_matched"
            }
        )
    
    return best