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
import cleaner
import loader
from src.config import PAGES_FILE, CHUNKS_FILE, PDFS_PATH

def split_page_to_chunks(page_record: dict, chunk_size: int = 1200, overlap: int = 200) -> Iterator[dict]:
    text = page_record["page_text"]

    if not text:
        return

    start = 0
    chunk_index = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()
        
        if chunk_text:
            chunk_index += 1
            yield {
                **{k: v for k, v in page_record.items() if k != "page_text"},
                "chunk_index": chunk_index,
                "chunk_id": f"{page_record['doc_id']}_p{page_record['page_number']:03d}_c{chunk_index:03d}",
                "chunk_text": chunk_text
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
    
    with out_path.open("w", encoding="utf-8") as f:
        for page_record in pages_iter:
            f.write(json.dumps(page_record, ensure_ascii=False) + "\n")
            count += 1
            
    return count
   
print("\n")
def iter_pages_cleaned():
    for pdf in PDFS_PATH:
        for page in loader.full_extract_document(pdf):
            clean_text = cleaner.clean_text(page["page_text"])
            page["page_text"] = clean_text
            yield page

# write_pages_to_jsonl(iter_pages_cleaned(), PAGES_FILE)
# write_chunks_to_jsonl(iter_pages_cleaned(), CHUNKS_FILE)