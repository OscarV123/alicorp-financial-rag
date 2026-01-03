import src.config as config
import src.ingest.splitter as splitter
import src.ingest.build_index as build_index
import src.rag.qa as qa

#=================================================================
#splitter.write_pages_to_jsonl(splitter.iter_pages_cleaned(), config.PAGES_FILE)
#splitter.write_chunks_to_jsonl(splitter.iter_pages_cleaned(), config.CHUNKS_FILE)
#=================================================================
#oai, collection = build_index.get_clients()
#
#total_read = 0
#total_indexed = 0
#batch_num = 0
#
#chunks_gen = build_index.iter_chunks_from_file(config.CHUNKS_FILE)
#
#for batch in build_index.batch_iter(chunks_gen, config.BATCH_SIZE):
#    batch_num += 1
#    total_read += len(batch)
#    
#    added = build_index.index_batch(collection, oai, batch)
#    total_indexed += added
#    
#    print(f"Batch {batch_num}: leídos={len(batch)} | indexados={added} | acum_leídos={total_read} | acum_indexados={total_indexed}")
#
#print("\nIndexación finalizada")
#print(f"Total chunks leídos: {total_read}")
#print(f"Total chunks indexados: {total_indexed}")
#print(f"Vector store: {config.CHROMA_PATH} | Colección: rag_finanzas")
#=================================================================
while True:
    q = input("Pregunta: ").strip()
    if not q:
        continue
    if q.lower() in ("exit", "salir", "quit"):
        break

    # mode = "strict" | "explanatory"
    res = qa.answer_question(
        question=q,
        where=None,       
        temperature=0.1,
        mode="strict"
    )

    print("\n--- RESPUESTA ---")
    print(res.answer)

    print("\n--- EVIDENCIA (debug) ---")
    for i, ev in enumerate(res.evidences, start=1):
        m = ev.metadata
        print(f"[{i}] {m.get('doc_id')} pág.{m.get('page_number')} | dist={ev.distance:.4f}")
        print(f"    chunk_id={ev.chunk_id}")
    print()
