#!/usr/bin/env python3
"""
Ingest HR policy documents into Supabase with embeddings.

Usage:
  python ingest_docs.py --tenant-id <uuid> --file handbook.pdf --title "Employee Handbook"
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from db.supabase_client import get_supabase
from services.gemini import embed_document_chunk
import PyPDF2


CHUNK_SIZE = 800    # characters
CHUNK_OVERLAP = 100


def extract_text_from_pdf(path: str) -> str:
    text = ""
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text


def chunk_text(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - CHUNK_OVERLAP
    return chunks


def ingest(tenant_id: str, file_path: str, title: str) -> None:
    sb = get_supabase()

    print(f"📄 Extracting text from {file_path}...")
    text = extract_text_from_pdf(file_path)
    print(f"   {len(text)} characters extracted")

    chunks = chunk_text(text)
    print(f"   {len(chunks)} chunks created")

    # Create document record
    doc_result = sb.table("hr_documents").insert({
        "tenant_id": tenant_id,
        "title": title,
        "file_path": file_path,
    }).execute()
    doc_id = doc_result.data[0]["id"]
    print(f"   Document ID: {doc_id}")

    # Embed and insert chunks
    for i, chunk in enumerate(chunks):
        print(f"   Embedding chunk {i+1}/{len(chunks)}...", end="\r")
        embedding = embed_document_chunk(chunk)
        sb.table("doc_chunks").insert({
            "tenant_id": tenant_id,
            "document_id": doc_id,
            "content": chunk,
            "embedding": embedding,
            "chunk_index": i,
        }).execute()

    print(f"\n✅ Done. {len(chunks)} chunks ingested for '{title}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--title", required=True)
    args = parser.parse_args()

    ingest(args.tenant_id, args.file, args.title)
