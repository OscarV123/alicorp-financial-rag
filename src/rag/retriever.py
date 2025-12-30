# ====================================================================================l
# Retriever (pregunta -> evidencia relevante).                                        |
#                                                                                     |
# Responsabilidad:                                                                    |
# - Recibir una pregunta y recuperar los chunks más relevantes desde el vector store. |
# - Aplicar reglas de búsqueda y/o filtros por metadata (ej. año, tipo de documento). |
# - Devolver evidencia lista para ser usada como contexto por el generador.           |
#                                                                                     |
# No hace:                                                                            |
# - No redacta la respuesta final (eso es del QA).                                    |
# - No define la política de respuesta (eso es del prompt).                           |
# ====================================================================================|
from dataclasses import dataclass
from typing import Dict
from src.ingest.build_index import get_clients, embed_texts
from openai import OpenAI
from typing import List, Any, Optional
from src.config import TOP_K
from typing import Dict, Any, Tuple
from src.rag.retriever_utils import detect_signals, SignalMatch

@dataclass
class Evidence:
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    distance: float

def embed_query(oai: OpenAI, question: str) -> List[float]:
    return embed_texts(oai, [question])[0]

def normalize_where(where: Dict[str, Any]) -> Dict[str, Any]:
    if not where:
        return {}
    
    if any(k.startswith("$") for k in where.keys()):
        return where
    
    items = [{k: v} for k, v in where.items()]

    if len(items) == 1:
        return items[0]
    
    return {"$and": items}

def query_collection(collection,
                     query_vector: List[float],
                     top_k: int,
                     where: Optional[Dict[str, Any]] = None):
    
    kwargs = {
        "query_embeddings": [query_vector],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"]
    }
    
    if where:
        kwargs["where"] = normalize_where(where)

    return collection.query(**kwargs)    

def get_evidence(result) -> List[Evidence]:
    docs = result.get("documents", [[]])[0] or []
    metas = result.get("metadatas", [[]])[0] or []
    dists = result.get("distances", [[]])[0] or []

    evidences: List[Evidence] = []

    for doc, meta, dist in zip(docs, metas, dists):
        evidences.append(
            Evidence(
                chunk_id=str(meta.get("chunk_id", "")),
                text=doc,
                metadata=meta,
                distance=float(dist)
            )
        )

    return evidences

def retrieve(question: str,
             top_k: int=TOP_K,
             where: Optional[Dict[str, Any]]=None,
             return_debug: bool=True) -> List[Evidence] | Tuple[List[Evidence], SignalMatch]:
    
    oai, collection = get_clients()
    query_vector = embed_query(oai, question)

    match_r = detect_signals(question)
    effective_where = where if where is not None else match_r.where

    result = query_collection(collection, query_vector, top_k, effective_where)
    evidences = get_evidence(result)

    if not evidences and effective_where:
        if "period" in effective_where:
            relaxed = dict(effective_where)
            relaxed.pop("period", None)
            result = query_collection(collection, query_vector, top_k, relaxed)
            evidences = get_evidence (result)
    
    if not evidences and effective_where and "year" in effective_where:
        relaxed = dict(effective_where)
        relaxed.pop("year", None)
        result = query_collection(collection, query_vector, top_k, relaxed)
        evidences = get_evidence(result)

    if not evidences:
        result = query_collection(collection, query_vector, top_k, None)
        evidences = get_evidence(result)

    if return_debug:
        return evidences, match_r
    
    return evidences