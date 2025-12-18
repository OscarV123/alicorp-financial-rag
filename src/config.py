"""
Configuración central del proyecto RAG-Alicorp.

Qué contiene:
- Rutas base (data/raw, data/processed, vector_store).
- Parámetros de chunking (tamaño y solapamiento).
- Parámetros de retrieval (top-k, filtros por metadata).
- Parámetros de modelos (embeddings y LLM) leídos desde variables de entorno.

Propósito:
- Evitar valores “hardcodeados” en el resto del proyecto.
- Permitir cambiar el comportamiento del pipeline desde un solo lugar.
"""
