# ==============================================================================l
# Indexación (chunks -> embeddings -> vector store).                            |
#                                                                               |
# Responsabilidad:                                                              |
# - Tomar los chunks ya preparados y construir/actualizar la base vectorial.    |
# - Persistir embeddings + metadata en vector_store para consultas posteriores. |
# - Ejecutarse como proceso de ingesta (offline/batch), no en cada pregunta.    |
#                                                                               |
# No hace:                                                                      |
# - No responde preguntas.                                                      |    
# - No invoca el LLM para generar respuestas.                                   |
# ==============================================================================|
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Iterator, Set
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from src.config import CHUNKS_FILE, CHROMA_PATH, BATCH_SIZE, EMBED_MODEL, API_KEY

def iter_chunks_from_file(chunks_file_path: Path) -> Iterator[Dict[str, Any]]:
    if not chunks_file_path.exists():
        raise FileNotFoundError(f"El archivo {chunks_file_path} no existe.")
    
    with chunks_file_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                chunk_record = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Error al parsear JSON en la línea {line_no} del archivo {chunks_file_path}: {e}") from e
        
            if "chunk_id" not in chunk_record or "chunk_text" not in chunk_record:
                raise ValueError(f"El registro en la línea {line_no} del archivo {chunks_file_path} carece de 'chunk_id' o 'chunk_text'.")
            
            yield chunk_record

def batch_iter(chunks_generator: Iterator[Dict[str, Any]], batch_size: int) -> Iterator[List[Dict[str, Any]]]:
    batch: List[Dict[str, Any]] = []
    for item in chunks_generator:
        batch.append(item)
        
        if len(batch) >= batch_size:
            yield batch
            batch = []
        
    if batch:
        yield batch

def get_clients() -> tuple[OpenAI, chromadb.api.Collection]:
    if not API_KEY:
        raise ValueError("La variable de entorno OPENAI_API_KEY no fue encontrada.")
    
    oai = OpenAI(api_key=API_KEY)
    
    chroma = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=Settings(anonymized_telemetry=False)
    )
    
    collection = chroma.get_or_create_collection(
        name="rag_finanzas",
        metadata={"hnsw:space": "cosine"}
    )
    
    return oai, collection

def filter_existing_chunk_ids(collection: chromadb.api.Collection, chunk_ids: List[str]) -> Set[str]:
    if collection.count() == 0:
        return set()
    
    existing_ids: Set[str] = set()
    step = 500

    for i in range(0, len(chunk_ids), step):
        batch_ids = chunk_ids[i:i+step]
        results = collection.get(ids=batch_ids, include=[])
        
        ids_found = results.get("ids", []) if results else []

        for _id in ids_found:
            if isinstance(_id, list):
                existing_ids.update(_id)
            else:
                existing_ids.add(_id)
    
    return existing_ids

def embed_texts(oai: OpenAI, texts: List[str]) -> List[List[float]]:
    resp = oai.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]

def index_batch(collection: chromadb.api.Collection, oai: OpenAI, batch: List[Dict[str, Any]]) -> int:
    ids = [c["chunk_id"] for c in batch]
    existing = filter_existing_chunk_ids(collection, ids)
    new = [c for c in batch if c["chunk_id"] not in existing]
    
    if not new:
        return 0

    documents: List[str] = [c["chunk_text"] for c in new]
    metadatas = []
    new_ids = []

    for c in new:
        new_ids.append(c["chunk_id"])
        m = dict(c)
        m.pop("chunk_text", None)
        metadatas.append(m)
    
    vectors = embed_texts(oai, documents)

    collection.add(
        ids=new_ids,
        documents=documents,
        embeddings=vectors,
        metadatas=metadatas
    )

    return len(new_ids)


