from src.ingest.splitter import write_chunks_to_jsonl, write_pages_to_jsonl
from src.config import PAGES_FILE, CHUNKS_FILE, BATCH_SIZE, CHROMA_PATH, EMBED_MODEL
from src.ingest.splitter import iter_pages_cleaned
from src.ingest.build_index import get_clients, iter_chunks_from_file, batch_iter, index_batch


#oai, collection = get_clients()
#
#total_read = 0
#total_indexed = 0
#batch_num = 0
#
#chunks_gen = iter_chunks_from_file(CHUNKS_FILE)
#
#for batch in batch_iter(chunks_gen, BATCH_SIZE):
#    batch_num += 1
#    total_read += len(batch)
#    
#    added = index_batch(collection, oai, batch)
#    total_indexed += added
#    
#    print(f"Batch {batch_num}: leídos={len(batch)} | indexados={added} | acum_leídos={total_read} | acum_indexados={total_indexed}")
#
#print("\nIndexación finalizada")
#print(f"Total chunks leídos: {total_read}")
#print(f"Total chunks indexados: {total_indexed}")
#print(f"Vector store: {CHROMA_PATH} | Colección: rag_finanzas")

#=================================================================

#write_pages_to_jsonl(iter_pages_cleaned(), PAGES_FILE)
#write_chunks_to_jsonl(iter_pages_cleaned(), CHUNKS_FILE)

#=================================================================

from src.rag.qa import answer_question

while True:
    q = input("Pregunta: ").strip()
    if not q:
        continue
    if q.lower() in ("exit", "salir", "quit"):
        break

    res = answer_question(
        question=q,
        where=None,       
        temperature=0.1
    )

    print("\n--- RESPUESTA ---")
    print(res.answer)

    print("\n--- EVIDENCIA (debug) ---")
    for i, ev in enumerate(res.evidences, start=1):
        m = ev.metadata
        print(f"[{i}] {m.get('doc_id')} pág.{m.get('page_number')} | dist={ev.distance:.4f}")
        print(f"    chunk_id={ev.chunk_id}")
    print()
