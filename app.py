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
