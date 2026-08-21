"""
Gemini is kept only for embeddings — Llama 3.3 70B (services/llama.py) doesn't
offer an embeddings endpoint, and the Supabase pgvector column is dimensioned
for Gemini's embedding model (vector(768)). All chat generation and intent
classification now runs on Llama; see services/llama.py.
"""
from google import genai
from google.genai import types
from config import get_settings

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=get_settings().gemini_api_key)
    return _client



def embed_text(text: str) -> list[float]:
    result = _get_client().models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY", output_dimensionality=768),
    )
    return result.embeddings[0].values


def embed_document_chunk(text: str) -> list[float]:
    result = _get_client().models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT", output_dimensionality=768),
    )
    return result.embeddings[0].values
