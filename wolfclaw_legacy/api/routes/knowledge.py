"""
Wolfclaw V3 — Knowledge Base API Routes (Phase 13)

Upload documents to a bot's knowledge base, search, list, and delete.
"""

import os
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from core import local_db
from core.rag_engine import chunk_text, extract_keywords, search_chunks

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


# ─────────── UPLOAD ───────────

@router.post("/upload")
async def upload_knowledge_doc(
    bot_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload a document to a bot's knowledge base. Chunks and indexes it."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Restricted to Desktop.")

    allowed_ext = {'.pdf', '.docx', '.txt', '.csv', '.md'}
    filename = file.filename or "unknown.txt"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed: {', '.join(allowed_ext)}")

    try:
        content_bytes = await file.read()

        # Extract text based on file type
        if ext == '.pdf':
            from PyPDF2 import PdfReader
            import io
            reader = PdfReader(io.BytesIO(content_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext == '.docx':
            from docx import Document
            import io
            doc = Document(io.BytesIO(content_bytes))
            text = "\n".join(p.text for p in doc.paragraphs)
        elif ext in {'.txt', '.csv', '.md'}:
            text = content_bytes.decode('utf-8', errors='replace')
        else:
            raise HTTPException(status_code=400, detail="Cannot parse file.")

        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="Document appears to be empty.")

        # Chunk the text
        chunks = chunk_text(text, chunk_size=500, overlap=50)

        if not chunks:
            raise HTTPException(status_code=400, detail="Could not extract meaningful text from document.")

        # Save doc record
        doc_id = local_db.save_knowledge_doc(bot_id, filename, len(chunks))

        # Build and save chunks with keywords
        db_chunks = []
        for i, chunk_content in enumerate(chunks):
            keywords = extract_keywords(chunk_content)
            db_chunks.append({
                'id': str(uuid.uuid4()),
                'bot_id': bot_id,
                'doc_id': doc_id,
                'doc_name': filename,
                'chunk_index': i,
                'content': chunk_content,
                'keywords': ','.join(keywords)
            })

        local_db.save_knowledge_chunks(db_chunks)

        return {
            "status": "success",
            "doc_id": doc_id,
            "filename": filename,
            "chunks_created": len(chunks),
            "message": f"✅ '{filename}' ingested into knowledge base ({len(chunks)} chunks)"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


# ─────────── LIST DOCS ───────────

@router.get("/{bot_id}")
async def list_knowledge_docs(bot_id: str):
    """List all documents in a bot's knowledge base."""
    try:
        docs = local_db.get_knowledge_docs(bot_id)
        return {"status": "success", "documents": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────── DELETE DOC ───────────

@router.delete("/{doc_id}")
async def delete_knowledge_doc(doc_id: str):
    """Delete a document and all its chunks from the knowledge base."""
    try:
        local_db.delete_knowledge_doc(doc_id)
        return {"status": "success", "message": "Document and chunks deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────── SEARCH ───────────

class SearchRequest(BaseModel):
    bot_id: str
    query: str
    top_k: int = 5

@router.post("/search")
async def search_knowledge(req: SearchRequest):
    """Search a bot's knowledge base for relevant chunks."""
    try:
        all_chunks = local_db.get_knowledge_chunks_for_bot(req.bot_id)
        if not all_chunks:
            return {"status": "success", "results": [], "message": "No knowledge base for this bot."}

        results = search_chunks(req.query, all_chunks, top_k=req.top_k)
        # Remove internal scoring from response
        for r in results:
            r.pop('_score', None)

        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
