"""
Phase 14 — File/Document Drop Zone (RAG Chat)
Upload PDF, DOCX, CSV, TXT and ask questions about the content.
"""
import os
import uuid
import tempfile
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from core.local_db import get_key_local
from auth.supabase_client import get_current_user

router = APIRouter()

# In-memory doc store for current session
_doc_store = {}

def _extract_text(file_path: str, filename: str) -> str:
    """Extract text from various file formats."""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif ext == ".csv":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif ext == ".pdf":
        try:
            import PyPDF2
            text = ""
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return text
        except ImportError:
            # Fallback: read raw bytes
            with open(file_path, "rb") as f:
                return f.read().decode("utf-8", errors="ignore")

    elif ext in (".docx", ".doc"):
        try:
            import docx
            doc = docx.Document(file_path)
            return "\n".join([p.text for p in doc.paragraphs])
        except ImportError:
            raise HTTPException(status_code=400, detail="python-docx not installed. Install with: pip install python-docx")

    elif ext == ".md":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Supported: .txt, .csv, .pdf, .docx, .md")


@router.post("/chat/upload-doc")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document for RAG chat. Returns a doc_id to reference in questions."""
    # Save to temp
    suffix = os.path.splitext(file.filename)[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    content = await file.read()
    tmp.write(content)
    tmp.close()

    try:
        text = _extract_text(tmp.name, file.filename)
    finally:
        os.unlink(tmp.name)

    if not text or len(text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Could not extract meaningful text from the file.")

    doc_id = str(uuid.uuid4())[:8]
    _doc_store[doc_id] = {
        "filename": file.filename,
        "text": text[:50000],  # Cap at 50k chars
        "char_count": len(text)
    }

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "chars_extracted": len(text),
        "message": f"✅ Document '{file.filename}' uploaded! Use doc_id '{doc_id}' to ask questions."
    }


@router.post("/chat/ask-doc")
async def ask_document(doc_id: str = Form(...), question: str = Form(...)):
    """Ask a question about a previously uploaded document."""
    if doc_id not in _doc_store:
        raise HTTPException(status_code=404, detail="Document not found. Upload first via /chat/upload-doc.")

    doc = _doc_store[doc_id]
    user = get_current_user()
    user_id = user["id"] if user else "local_user"

    # Build RAG prompt
    system_prompt = (
        f"You are a document analysis assistant. The user has uploaded a document called '{doc['filename']}'. "
        f"Answer their question based ONLY on the document content below. If the answer is not in the document, say so.\n\n"
        f"--- DOCUMENT CONTENT ---\n{doc['text'][:30000]}\n--- END DOCUMENT ---"
    )

    # Try providers
    providers = [
        ("openai", "openai/gpt-4o"),
        ("anthropic", "anthropic/claude-3-5-sonnet-20240620"),
        ("google", "google/gemini-1.5-flash"),
    ]

    for provider_name, model in providers:
        api_key = get_key_local(user_id, f"{provider_name}_key")
        if api_key:
            try:
                from core.wolf_engine import get_llm_response
                response = get_llm_response(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question}
                    ],
                    api_key=api_key
                )
                return {
                    "doc_id": doc_id,
                    "filename": doc["filename"],
                    "question": question,
                    "answer": response,
                    "provider": provider_name
                }
            except Exception:
                continue

    raise HTTPException(status_code=400, detail="No API key found. Add one in Settings.")


@router.get("/chat/docs")
async def list_uploaded_docs():
    """List all documents currently in the session store."""
    return {
        "docs": [
            {"doc_id": did, "filename": d["filename"], "chars": d["char_count"]}
            for did, d in _doc_store.items()
        ]
    }
