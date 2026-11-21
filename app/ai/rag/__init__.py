"""
Retrieval-Augmented Generation over uploaded documentation.

    upload ─► extract ─► clean ─► chunk ─► embed ─► ChromaDB   (ingest.py)
    question ─► embed ─► nearest chunks ─► context ─► LLM ─► answer + sources
                                                      (retrieval.py, answer.py)

Design choices a reviewer should know:
* Chunk TEXT lives in SQL (``document_chunks``) and in ChromaDB; the vector
  only in ChromaDB. SQL is the source of truth for listing and deletion.
* Embeddings come from an OpenAI-compatible ``/embeddings`` endpoint so the
  same configuration works for OpenAI and for a local Ollama server.
* Retrieved text is untrusted: it is wrapped in delimited blocks and the
  model is told to treat it as data, never as instructions.
"""
