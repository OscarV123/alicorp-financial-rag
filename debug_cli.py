from pathlib import Path
from pdb import run
import sys
from src.rag.retriever import retrieve
import src.config as config
import src.ingest.build_index as build_index
import src.rag.qa as qa
import app as api_endpoints


# Reingestar BD vectorial desde archivos de texto estructurado (chunks_output_*.txt)
#
#from pathlib import Path
#import src.ingest.build_index as build_index
#
#def reiniciar_y_reingestar():
#    print("Iniciando limpieza del vector store...")
#    build_index.clear_entire_collection()
#    
#    oai, collection = build_index.get_clients()
#    
#    directorio_txt = Path("data/output_chunks") 
#    
#    if not directorio_txt.exists():
#        print(f"Error: No se encuentra el directorio {directorio_txt}. "
#              f"Asegúrate de haber ejecutado primero tu pipeline de procesamiento (run).")
#        return
#
#    print("\nComenzando la indexación de los nuevos archivos de texto...")
#    
#    for txt_file in directorio_txt.glob("*.txt"):
#        print(f"-> Indexando desde archivo: {txt_file.name}")
#        
#        chunks_generator = build_index.iter_chunks_from_file(txt_file)
#        
#        lotes = build_index.batch_iter(chunks_generator, batch_size=64)
#        
#        total_documento = 0
#        for lote in lotes:
#            cant_indexados = build_index.index_batch(collection, oai, lote, force_update=True)
#            total_documento += cant_indexados
#            
#        print(f"   ¡Éxito! Se indexaron {total_documento} chunks para {txt_file.name}")
#
#    print("\n=== PROCESO TERMINADO: Tu RAG ahora está 100% limpio y actualizado ===")
#
#
#reiniciar_y_reingestar()
#
#
#=================================================================
#
#MARKER_RESULTS_DIR = Path(r"C:\Proyectos\alicorp-financial-rag\data\processed")
#RAW_DIR = Path(r"C:\Proyectos\alicorp-financial-rag\data\raw")
#PROCESSED_DIR = Path(r"C:\Proyectos\alicorp-financial-rag\data\processed")
#
#TEST_EMPRESA = "Alicorp"
#
#archivos_md = list(MARKER_RESULTS_DIR.rglob("*.md"))
#
#if not archivos_md:
#    print("No se encontraron archivos .md en el directorio de conversión.")
#else:
#    print(f"Se detectaron {len(archivos_md)} documentos para procesar.\n")
#
#for md_path in archivos_md:
#    doc_name = md_path.stem 
#    
#    candidatos_pdf = list(RAW_DIR.rglob(f"{doc_name}.pdf"))
#    
#    if not candidatos_pdf:
#        print(f"Alerta: No se encontró el PDF original para '{doc_name}.pdf' en {RAW_DIR}. Se omitirá.")
#        continue
#        
#    pdf_path = candidatos_pdf[0]
#    
#    output_txt_path = PROCESSED_DIR / f"chunks_output_{doc_name}.txt"
#
#    try:
#        run(
#            md_path=md_path,
#            pdf_path=pdf_path,
#            output_txt_path=output_txt_path,
#            empresa=TEST_EMPRESA
#        )
#    except Exception as e:
#        print(f"Error crítico al procesar {doc_name}: {e}")
#        print("Continuando con el siguiente archivo...\n")
#
#print("\n¡Procesamiento dinámico en lote finalizado por completo!")
#
#=================================================================
#
#PROCESSED_DIR = Path(r"C:\Proyectos\alicorp-financial-rag\data\processed")
#BATCH_SIZE = 100
#
#try:
#    # Configurar Clientes
#    openai_client, chroma_collection = build_index.get_clients()
#    print(f"Conexión establecida con ChromaDB. Elementos actuales: {chroma_collection.count()}")
#    
#    archivos_txt = list(PROCESSED_DIR.glob("chunks_output_*.txt"))
#    
#    if not archivos_txt:
#        print("No se encontraron archivos 'chunks_output_*.txt' en el directorio processed.")
#    else:
#        print(f"Se detectaron {len(archivos_txt)} archivos de texto estructurado para procesar.")
#        
#        for txt_path in archivos_txt:
#            print(f"\nIndexando documento: {txt_path.name}")
#            
#            # Inicializar el generador modificado
#            chunks_generator = build_index.iter_chunks_from_file(txt_path)
#            
#            total_nuevos_en_archivo = 0
#            
#            # Procesar por lotes (Batching) para optimizar la API de OpenAI
#            for batch in build_index.batch_iter(chunks_generator, batch_size=BATCH_SIZE):
#                nuevos_insertados = build_index.index_batch(chroma_collection, openai_client, batch)
#                total_nuevos_en_archivo += nuevos_insertados
#                print(f"   -> Procesados {len(batch)} chunks. Insertados nuevos: {nuevos_insertados}")
#            
#            print(f"Finalizado {txt_path.name}. Total nuevos indexados: {total_nuevos_en_archivo}")
#            
#    print(f"\nPipeline de indexación completado. Elementos totales finales en Chroma: {chroma_collection.count()}")
#    
#except Exception as e:
#    print(f"\nError crítico durante la ejecución del pipeline: {e}")
#
#=================================================================
#while True:
#        q = input("Pregunta: ").strip()
#        if not q:
#            continue
#        if q.lower() in ("exit", "salir", "quit"):
#            print("Saliendo del modo de prueba del retriever.")
#            break
#        
#        try:
#            # Ejecutamos la recuperación de información (Top K chunks)
#            resultados, debug_info = retrieve(q, top_k=3)
#            
#            print("\n--- FILTROS SEMÁNTICOS DETECTADOS ---")
#            print(f"   -> Categoría de señal: {debug_info.key}")
#            print(f"   -> Filtro 'where' estructurado: {debug_info.where}")
#            if "where_conflicts" in debug_info.debug:
#                print(f"   Conflictos resueltos: {debug_info.debug['where_conflicts']}")
#            
#            print("\n --- EVIDENCIA RECUPERADA (ChromaDB) ---")
#            if not resultados:
#                print("    No se encontró ninguna evidencia con los filtros aplicados.")
#            else:
#                for idx, ev in enumerate(resultados, start=1):
#                    m = ev.metadata
#                    print(f"[{idx}] Doc: {m.get('doc_id')} | Pág. Estimada: {m.get('page_number')} | Distancia: {ev.distance:.4f}")
#                    print(f"    chunk_id = {ev.chunk_id}")
#                    # Mostramos los primeros 250 caracteres del texto para validar contenido
#                    texto_resumido = ev.text.replace('\n', ' ').strip()
#                    print(f"    Texto: {texto_resumido[:250]}...")
#                    print("-" * 60)
#            print() # Salto de línea estético antes de la siguiente pregunta
#            
#        except Exception as e:
#            print(f"\nError al procesar la búsqueda: {e}\n")
#================================================================ 
#
#sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
#
print("================================================================")
print("SISTEMA EXPERTO RAG - ALICORP FINANCIAL QA INTERACTIVE CLI")
print("================================================================")
print("Escribe tu consulta financiera o de Hechos de Importancia.")
print("Escribe 'salir' o 'exit' para cerrar la sesión.\n")

while True:
    q = input("Pregunta: ").strip()
    if not q:
        continue
    if q.lower() in ("exit", "salir", "quit"):
        print("Cerrando pipeline de consulta. ¡Hasta luego!")
        break
    
    res = qa.answer_question(
        question=q,
        explicit_where=None,    
        temperature=0.1,
        mode="strict"
    )

    print("\n--- RESPUESTA DEL LLM ---")
    print(res.answer)

    print("\n--- EVIDENCIA DE RESPALDO (Citas) ---")
    for i, ev in enumerate(res.evidences, start=1):
        m = ev.metadata
        print(f"[{i}] Doc ID: {m.get('doc_id')} | Pág: {m.get('page_number')} | Distancia: {ev.distance:.4f}")
        print(f"    chunk_id = {ev.chunk_id}")
    print("\n" + "="*80 + "\n")