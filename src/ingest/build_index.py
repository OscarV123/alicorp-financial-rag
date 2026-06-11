# ==============================================================================
# Indexación (chunks -> embeddings -> vector store).                           |
# ==============================================================================
import os
import json
import re
import ast
from pathlib import Path
from typing import List, Dict, Any, Iterator, Set
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from src.config import CHROMA_PATH, EMBED_MODEL

def iter_chunks_from_file(chunks_file_path: Path) -> Iterator[Dict[str, Any]]:
    """
    Lee los archivos de verificación con separadores '===' y reconstruye
    los diccionarios necesarios para ChromaDB usando expresiones regulares.
    """
    if not chunks_file_path.exists():
        raise FileNotFoundError(f"El archivo {chunks_file_path} no existe.")
    
    with chunks_file_path.open("r", encoding="utf-8") as f:
        full_text = f.read()
    
    chunk_pattern = re.compile(
        r"={70}\nCHUNK (\d+)\nMetadata: (\{.*?\})\n={70}\n(.*?)(?=\n={70}\nCHUNK \d+|\Z)", 
        re.DOTALL
    )
    
    matches = chunk_pattern.findall(full_text)
    
    for chunk_num, meta_str, content_str in matches:
        try:
            metadata = ast.literal_eval(meta_str.strip())
            chunk_text = content_str.strip()
            
            doc_id = metadata.get("doc_id", "documento")
            chunk_id = f"{doc_id}_chunk_{chunk_num}"
            
            chunk_record = {
                "chunk_id": chunk_id,
                "chunk_text": chunk_text
            }
            
            for k, v in metadata.items():
                chunk_record[k] = v
                
            yield chunk_record

        except Exception as e:
            print(f"Error al parsear el bloque del CHUNK {chunk_num} en {chunks_file_path.name}: {e}")
            continue

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
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("La variable de entorno OPENAI_API_KEY no fue encontrada.")
    
    oai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    chroma = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=Settings(anonymized_telemetry=False)
    )
    
    collection = chroma.get_or_create_collection(
        name="rag_finanzas",
        metadata={"hnsw:space": "cosine"}
    )
    
    return oai, collection

def clear_entire_collection():
    """
    ELIMINACIÓN TOTAL DE SEGURIDAD:
    Borra la colección completa de Chroma para forzar una ingesta limpia desde cero.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("La variable de entorno OPENAI_API_KEY no fue encontrada.")
        
    chroma = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=Settings(anonymized_telemetry=False)
    )
    try:
        chroma.delete_collection(name="rag_finanzas")
        print("⚠️ Colección 'rag_finanzas' eliminada por completo de ChromaDB.")
    except Exception as e:
        print(f"Aviso al intentar borrar colección (puede que no existiera): {e}")

def delete_document_from_index(collection: chromadb.api.Collection, doc_id: str):
    """
    ELIMINACIÓN SELECTIVA:
    Permite limpiar los chunks de un solo documento específico usando su doc_id.
    """
    try:
        collection.delete(where={"doc_id": doc_id})
        print(f"-> Eliminados del índice vectorial todos los chunks previos de: {doc_id}")
    except Exception as e:
        print(f"Error al limpiar selectivamente el documento {doc_id}: {e}")

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

def index_batch(collection: chromadb.api.Collection, oai: OpenAI, batch: List[Dict[str, Any]], force_update: bool = True) -> int:
    """
    Indexa un lote de chunks. 
    Si force_update es True, utiliza collection.upsert para sobreescribir los metadatos viejos.
    """
    ids = [c["chunk_id"] for c in batch]
    
    if not force_update:
        existing = filter_existing_chunk_ids(collection, ids)
        new = [c for c in batch if c["chunk_id"] not in existing]
    else:
        new = batch
    
    if not new:
        return 0

    documents: List[str] = [c["chunk_text"] for c in new]
    metadatas = []
    new_ids = []

    for c in new:
        new_ids.append(c["chunk_id"])
        
        m = dict(c)
        m.pop("chunk_text", None)
        m.pop("chunk_id", None) 
        
        metadata_limpia = {k: v for k, v in m.items() if v is not None}
        metadatas.append(metadata_limpia)
    
    vectors = embed_texts(oai, documents)

    if force_update:
        collection.upsert(
            ids=new_ids,
            documents=documents,
            embeddings=vectors,
            metadatas=metadatas
        )
    else:
        collection.add(
            ids=new_ids,
            documents=documents,
            embeddings=vectors,
            metadatas=metadatas
        )

    return len(new_ids)