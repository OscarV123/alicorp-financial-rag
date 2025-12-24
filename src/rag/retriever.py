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
from config import TOP_K

@dataclass
class Evidence:
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    distance: float

def embed_query(oai: OpenAI, question: str) -> List[float]:
    return embed_texts(oai, [question])[0]

def retrieve(question: str, top_k: int=TOP_K, where: Optional[Dict[str, Any]]=None) -> List[Evidence]:
    oai, collection = get_clients()
    query_vector = embed_query(oai, question)

    kwargs = {
        "query_embeddings": [query_vector],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"]
    }

    if where:
        kwargs["where"] = where

    result = collection.query(**kwargs)

    docs = result["documents"][0]
    metas = result["metadatas"][0]
    dists = result["distances"][0]

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