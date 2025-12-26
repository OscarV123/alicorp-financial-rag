# ============================================================================================l
# Chunking (contenido de páginas -> chunks).                                                  |  
#                                                                                             |  
# Responsabilidad:                                                                            |  
# - Transformar texto a nivel de página en fragments/chunks con solapamiento.                 |
# - Preservar trazabilidad: cada chunk debe poder mapearse a una página o rango de páginas.   |
#                                                                                             |  
# No hace:                                                                                    |
# - No genera embeddings.                                                                     |
# - No escribe en el vector store.                                                            |   
# ============================================================================================|
from typing import Iterator
import json
from pathlib import Path
from src.ingest.cleaner import clean_text
from src.ingest.loader import full_extract_document
from src.config import PDFS_PATH
from src.ingest.table_extractor import looks_like_table, extract_table_rows, extract_table_fact_total, normalize_for_table

def split_page_to_chunks(page_record: dict, chunk_size: int = 1200, overlap: int = 200) -> Iterator[dict]:
    raw_text = (page_record.get("page_text") or "")
    text = raw_text.strip()
    if not text:
        return

    chunk_index = 0

    text_norm = normalize_for_table(raw_text)

    doc_type = (page_record.get("doc_type") or "").lower()
    allow_table_mode = (doc_type == "important_facts")

    if allow_table_mode and looks_like_table(text_norm):
        emitted_any_table_chunk = False

        total_fact = extract_table_fact_total(page_record)
        if total_fact:
            chunk_index += 1
            emitted_any_table_chunk = True
            yield {
                **{k: v for k, v in total_fact.items() if k != "chunk_text"},
                "chunk_index": chunk_index,
                "chunk_type": total_fact.get("chunk_type", "table_fact_total"),
                "chunk_text": total_fact["chunk_text"],
            }

        for row_fact in extract_table_rows(page_record):
            chunk_index += 1
            emitted_any_table_chunk = True
            yield {
                **{k: v for k, v in row_fact.items() if k != "chunk_text"},
                "chunk_index": chunk_index,
                "chunk_type": row_fact.get("chunk_type", "table_fact_row"),
                "chunk_text": row_fact["chunk_text"],
            }

        if emitted_any_table_chunk:
            return

    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()

        if chunk_text:
            chunk_index += 1
            yield {
                **{k: v for k, v in page_record.items() if k != "page_text"},
                "chunk_index": chunk_index,
                "chunk_id": f"{page_record['doc_id']}_p{page_record['page_number']:03d}_c{chunk_index:03d}",
                "chunk_text": chunk_text,
            }

        if end == len(text):
            break

        start = max(0, end - overlap)

        
def write_chunks_to_jsonl(pages_iter: Iterator[dict], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    
    with out_path.open("w", encoding="utf-8") as f:
        for page_record in pages_iter:
            for chunk_record in split_page_to_chunks(page_record):
                f.write(json.dumps(chunk_record, ensure_ascii=False) + "\n")
                count += 1

def write_pages_to_jsonl(pages_iter: Iterator[dict], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    print(out_path)
    with out_path.open("w", encoding="utf-8") as f:
        for page_record in pages_iter:
            f.write(json.dumps(page_record, ensure_ascii=False) + "\n")
            count += 1
            
    return count
   
print("\n")
def iter_pages_cleaned():
    for pdf in PDFS_PATH.rglob("*.pdf"):
        for page in full_extract_document(pdf):
            clean_t = clean_text(page["page_text"])
            page["page_text"] = clean_t
            yield page
