import os
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
import PyPDF2
from docx import Document as DocxDocument
import csv
from core import local_db
from core.bot_manager import _get_active_workspace_id

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_CHARS = 50000

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and parse a document to the active workspace."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Document Uploads are currently a Desktop-only feature.")

    ws_id = _get_active_workspace_id()
    
    # Read file content safely
    try:
        raw_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    filename = file.filename.lower()
    text = ""

    try:
        if filename.endswith(".pdf"):
            import io
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(raw_bytes))
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"

        elif filename.endswith(".docx"):
            import io
            doc = DocxDocument(io.BytesIO(raw_bytes))
            text = "\n".join([p.text for p in doc.paragraphs])

        elif filename.endswith(".csv"):
            import io
            csv_reader = csv.reader(io.StringIO(raw_bytes.decode('utf-8')))
            for row in csv_reader:
                text += ", ".join(row) + "\n"

        elif filename.endswith(".txt") or filename.endswith(".md"):
            text = raw_bytes.decode('utf-8')

        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF, DOCX, CSV, TXT, or MD.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse document: {e}")

    # Truncate text if it's too long
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n\n...[Document Truncated due to size limit]..."

    if not text.strip():
        raise HTTPException(status_code=400, detail="No readable text found in document.")

    try:
        doc_id = local_db.save_document(ws_id, file.filename, text)
        return {
            "status": "success",
            "doc_id": doc_id,
            "filename": file.filename,
            "message": "Document parsed and saved securely."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.get("/")
async def list_documents():
    """List all documents in the active workspace."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Document Uploads are currently a Desktop-only feature.")
        
    ws_id = _get_active_workspace_id()
    try:
        docs = local_db.get_documents_for_workspace(ws_id)
        return {"documents": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document."""
    if os.environ.get("WOLFCLAW_ENVIRONMENT") != "desktop":
        raise HTTPException(status_code=403, detail="Document Uploads are currently a Desktop-only feature.")
        
    try:
        local_db.delete_document(doc_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
