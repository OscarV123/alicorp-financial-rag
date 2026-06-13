# ====================================================================================
# Retriever (pregunta -> evidencia relevante).                                       |
# ====================================================================================
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
from openai import OpenAI
import chromadb
from sentence_transformers import CrossEncoder
import src.config as config
import src.ingest.build_index as build_index
import src.rag.retriever_utils as retriever_utils
 
@dataclass
class Evidence:
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    distance: float
 
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def rerank_results(question: str, docs: List[Dict[str, Any]], top_k: int):
    pairs = [(question, doc['chunk_text']) for doc in docs]
    scores = reranker.predict(pairs)
    for i, doc in enumerate(docs):
        doc['score'] = float(scores[i]) 
    
    sorted_docs = sorted(docs, key=lambda x: x['score'], reverse=True)
    return sorted_docs[:top_k]

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
 
    stages: List[Tuple[str, Optional[Dict[str, Any]], int]] = []
    evidences: List[Evidence] = []
    last_where: Optional[Dict[str, Any]] = None
 
    multi_where = retriever_utils.build_multi_where(match_r)
    if multi_where is not None:
        primary_chain = retriever_utils.relaxation_chain(multi_where)
        stage_label = "multi_intent_where"
    else:
        primary_chain = retriever_utils.relaxation_chain(match_r.where)
        stage_label = "signal_where"
 
    for where_candidate in primary_chain:
        result = query_collection(collection, query_vector, top_k, where_candidate)
        evidences = get_evidence(result)
        stages.append((stage_label, where_candidate, len(evidences)))
        last_where = where_candidate
        if evidences:
            break
 
    if not evidences:
        fallback_keys = match_r.debug.get("multi_intent_keys") or [match_r.key]
        fallback_types = retriever_utils.doc_types_for_keys(fallback_keys)
        resguardo_where = {"doc_type": {"$in": fallback_types}} if fallback_types else None
 
        if resguardo_where is not None and resguardo_where != last_where:
            result = query_collection(collection, query_vector, top_k, resguardo_where)
            evidences = get_evidence(result)
            stages.append(("fallback_doc_type", resguardo_where, len(evidences)))
 
        if not evidences and resguardo_where is not None:
            result = query_collection(collection, query_vector, top_k, None)
            evidences = get_evidence(result)
            stages.append(("fallback_unfiltered", None, len(evidences)))
 
    match_r.debug["retrieval_stages"] = stages
    
    if evidences:
        docs_to_rerank = [{"chunk_text": ev.text, "evidence_obj": ev} for ev in evidences]
        reranked = rerank_results(question, docs_to_rerank, top_k)
        
        evidences = [d["evidence_obj"] for d in reranked]
        
        match_r.debug["reranked_scores"] = [d["score"] for d in reranked]

    if return_debug:
        if "reranked_scores" in match_r.debug:
            print(f"Reranked top score: {match_r.debug['reranked_scores'][0]}")
        return evidences, match_r

    return evidences