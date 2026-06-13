# ====================================================================================
# Retriever (pregunta -> evidencia relevante).                                       |
# ====================================================================================
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from openai import OpenAI
import chromadb
from sentence_transformers import CrossEncoder
import src.config as config
import src.ingest.build_index as build_index
import src.rag.retriever_utils as retriever_utils

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def rerank_results(question: str, docs: List[Dict[str, Any]], top_k=5):
    pairs = [(question, doc['chunk_text']) for doc in docs]
    
    scores = reranker.predict(pairs)
    
    # Asignar scores y ordenar
    for i, doc in enumerate(docs):
        doc['relevance_score'] = scores[i]
        
    return sorted(docs, key=lambda x: x['relevance_score'], reverse=True)[:top_k]

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

    match_r.debug["retrieval_stages"] = []
    evidences = []

    chain = retriever_utils.relaxation_chain(effective_where)
    
    for stage_idx, relaxed_where in enumerate(chain):
        result = query_collection(collection, query_vector, top_k * 2, relaxed_where)
        current_evidences = get_evidence(result)
        
        match_r.debug["retrieval_stages"].append({
            "stage": f"relaxation_chain_{stage_idx}",
            "where": relaxed_where,
            "results_count": len(current_evidences)
        })
        
        if current_evidences:
            evidences = current_evidences
            break

    if not evidences:
        resguardo_where = None
        if match_r.key in ["financial_statements", "financial_statements_fallback"]:
            resguardo_where = {"doc_type": {"$in": ["eeff_separados", "eeff_consolidados"]}}
            
        result = query_collection(collection, query_vector, top_k * 2, resguardo_where)
        evidences = get_evidence(result)
        
        match_r.debug["retrieval_stages"].append({
            "stage": "final_fallback",
            "where": resguardo_where,
            "results_count": len(evidences)
        })

    if evidences:
        docs_to_rerank = [{"chunk_text": ev.text, "evidence_obj": ev} for ev in evidences]
        
        reranked_docs = rerank_results(question, docs_to_rerank, top_k=top_k)
        
        evidences = [d["evidence_obj"] for d in reranked_docs]
        
        match_r.debug["reranked_scores"] = [d["relevance_score"] for d in reranked_docs]

    if return_debug:
        print(f"Reranked top score: {match_r.debug['reranked_scores'][0]}")
        return evidences, match_r

    return evidences