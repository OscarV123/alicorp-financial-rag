# ====================================================================================
# Retriever (pregunta -> evidencia relevante).                                       |
# ====================================================================================
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from openai import OpenAI
import chromadb

import src.config as config
import src.ingest.build_index as build_index
import src.rag.retriever_utils as retriever_utils

@dataclass
class Evidence:
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    distance: float

def embed_query(oai: OpenAI, question: str) -> List[float]:
    return build_index.embed_texts(oai, [question])[0]

def normalize_where(where: Dict[str, Any]) -> Dict[str, Any]:
    if not where:
        return {}

    if any(k.startswith("$") for k in where.keys()):
        return where
    
    items = [{k: v} for k, v in where.items()]
    if len(items) == 1:
        return items[0]
    
    return {"$and": items}

def query_collection(collection: chromadb.api.Collection,
                     query_vector: List[float],
                     top_k: int,
                     where: Optional[Dict[str, Any]] = None):
    
    kwargs = {
        "query_embeddings": [query_vector],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"]
    }
    
    if where:
        cleaned_where = normalize_where(where)
        if cleaned_where:
            kwargs["where"] = cleaned_where

    return collection.query(**kwargs)    

def get_evidence(result) -> List[Evidence]:
    ids = result.get("ids", [[]])[0] or []
    docs = result.get("documents", [[]])[0] or []
    metas = result.get("metadatas", [[]])[0] or []
    dists = result.get("distances", [[]])[0] or []

    evidences: List[Evidence] = []

    for chunk_id, doc, meta, dist in zip(ids, docs, metas, dists):
        evidences.append(
            Evidence(
                chunk_id=str(chunk_id),
                text=doc,
                metadata=meta,
                distance=float(dist)
            )
        )
    return evidences

def retrieve(question: str,
             top_k: int = config.TOP_K, 
             explicit_where: Optional[Dict[str, Any]] = None,
             return_debug: bool = True):

    oai, collection = build_index.get_clients()
    query_vector = embed_query(oai, question)

    match_r = retriever_utils.detect_signals(question)
    match_r = retriever_utils.merge_where(match_r, explicit_where)
    effective_where = match_r.where

    result = query_collection(collection, query_vector, top_k, effective_where)
    evidences = get_evidence(result)

    if not evidences and effective_where:
        if "period" in effective_where:
            relaxed = dict(effective_where)
            relaxed.pop("period", None)
            result = query_collection(collection, query_vector, top_k, relaxed)
            evidences = get_evidence(result)
            if not evidences:
                effective_where = relaxed

        if not evidences and "year" in effective_where:
            relaxed = dict(effective_where)
            relaxed.pop("year", None)
            result = query_collection(collection, query_vector, top_k, relaxed)
            evidences = get_evidence(result)

    if not evidences:
        question_lower = question.lower()
        palabras_financieras = ["informe", "eeff", "separado", "consolidado", "balance", "capital", "nota", "patrimonio"]
        
        if any(w in question_lower for w in palabras_financieras):
            resguardo_where = {"doc_type": {"$ne": "hechosdeimportancia_convocatoriaajuntadeaccionistas_febrero-2023"}}
        else:
            resguardo_where = None
            
        result = query_collection(collection, query_vector, top_k, resguardo_where)
        evidences = get_evidence(result)

    if return_debug:
        return evidences, match_r

    return evidences