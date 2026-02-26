"""
Wolfclaw V3 — RAG Engine (Retrieval-Augmented Generation)

Local-first knowledge base using TF-IDF keyword search.
No external APIs, no vector databases, fully offline.
"""

import re
import math
import uuid
from typing import List, Dict, Optional
from collections import Counter


# ─────────── TEXT CHUNKING ───────────

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks of approximately `chunk_size` words.
    Uses sentence boundaries when possible for cleaner chunks.
    """
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return []
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for sentence in sentences:
        word_count = len(sentence.split())
        
        # If a single sentence exceeds chunk_size, force-split it
        if word_count > chunk_size:
            # Flush current chunk first
            if current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_word_count = 0
            
            # Force-split the long sentence by words
            words = sentence.split()
            for i in range(0, len(words), chunk_size - overlap):
                chunk_words = words[i:i + chunk_size]
                chunks.append(' '.join(chunk_words))
            continue
        
        # If adding this sentence would exceed limit, finalize chunk
        if current_word_count + word_count > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            
            # Keep last few sentences for overlap
            overlap_text = ' '.join(current_chunk[-2:]) if len(current_chunk) >= 2 else ''
            current_chunk = [overlap_text] if overlap_text else []
            current_word_count = len(overlap_text.split()) if overlap_text else 0
        
        current_chunk.append(sentence)
        current_word_count += word_count
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks


# ─────────── KEYWORD EXTRACTION ───────────

# Common English stop words to filter out
STOP_WORDS = set("""
a an the is are was were be been being have has had do does did will would
shall should may might can could am is are was were been being have has had
do does did shall should will would may might can could must need dare ought
i me my myself we our ours ourselves you your yours yourself yourselves he
him his himself she her hers herself it its itself they them their theirs
themselves what which who whom this that these those and but or nor for yet
so both either neither not only also very too quite rather just about above
after again against all at before below between by during each few from
further get got had has here how if in into more most no now of off on
once only other out over own per same she so some still such than that the
then there therefore these through to too under until up very was we were
what when where which while who whom why with within without would
""".split())

def extract_keywords(text: str, max_keywords: int = 30) -> List[str]:
    """Extract the most significant keywords from text using term frequency."""
    # Tokenize: lowercase, remove punctuation, split
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Filter stop words
    words = [w for w in words if w not in STOP_WORDS]
    
    # Count frequencies
    freq = Counter(words)
    
    # Return top keywords
    return [word for word, _ in freq.most_common(max_keywords)]


# ─────────── TF-IDF SEARCH ───────────

def _compute_tf(text: str) -> Dict[str, float]:
    """Compute term frequency for a text."""
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    words = [w for w in words if w not in STOP_WORDS]
    total = len(words)
    if total == 0:
        return {}
    freq = Counter(words)
    return {word: count / total for word, count in freq.items()}


def _compute_idf(documents: List[str]) -> Dict[str, float]:
    """Compute inverse document frequency across all documents."""
    n_docs = len(documents)
    if n_docs == 0:
        return {}
    
    # Count how many documents each word appears in
    doc_freq = Counter()
    for doc in documents:
        words = set(re.findall(r'\b[a-zA-Z]{3,}\b', doc.lower()))
        words = {w for w in words if w not in STOP_WORDS}
        doc_freq.update(words)
    
    return {word: math.log(n_docs / (1 + count)) for word, count in doc_freq.items()}


def search_chunks(query: str, chunks: List[Dict], top_k: int = 5) -> List[Dict]:
    """
    Search chunks using TF-IDF scoring.
    
    Args:
        query: The search query
        chunks: List of dicts with 'content' and 'keywords' fields
        top_k: Number of top results to return
    
    Returns:
        List of chunks sorted by relevance score (highest first)
    """
    if not chunks or not query.strip():
        return []
    
    # Extract query terms
    query_terms = set(re.findall(r'\b[a-zA-Z]{3,}\b', query.lower()))
    query_terms = {w for w in query_terms if w not in STOP_WORDS}
    
    if not query_terms:
        return chunks[:top_k]
    
    # Compute IDF across all chunk contents
    all_contents = [c['content'] for c in chunks]
    idf = _compute_idf(all_contents)
    
    # Score each chunk
    scored = []
    for chunk in chunks:
        tf = _compute_tf(chunk['content'])
        
        # TF-IDF score for query terms
        score = 0.0
        for term in query_terms:
            tf_val = tf.get(term, 0)
            idf_val = idf.get(term, 0)
            score += tf_val * idf_val
        
        # Bonus: boost if query terms appear in keywords
        if chunk.get('keywords'):
            keyword_list = chunk['keywords'].split(',')
            keyword_matches = sum(1 for k in keyword_list if k.strip().lower() in query_terms)
            score += keyword_matches * 0.1
        
        if score > 0:
            scored.append({**chunk, '_score': score})
    
    # Sort by score descending
    scored.sort(key=lambda x: x['_score'], reverse=True)
    
    return scored[:top_k]


def format_context_for_prompt(chunks: List[Dict], max_tokens: int = 2000) -> str:
    """
    Format retrieved chunks into a context string for injection into the system prompt.
    """
    if not chunks:
        return ""
    
    context_parts = []
    total_words = 0
    
    for i, chunk in enumerate(chunks, 1):
        content = chunk['content']
        word_count = len(content.split())
        
        if total_words + word_count > max_tokens:
            break
        
        source = chunk.get('doc_name', 'Unknown Document')
        context_parts.append(f"[Source: {source} | Chunk {chunk.get('chunk_index', i)}]\n{content}")
        total_words += word_count
    
    if not context_parts:
        return ""
    
    return "## KNOWLEDGE BASE CONTEXT\nThe following excerpts from the user's knowledge base are relevant to this conversation. Use them to provide accurate, grounded answers.\n\n" + "\n\n---\n\n".join(context_parts)
