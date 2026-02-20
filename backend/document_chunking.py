"""
Document Chunking Utilities for Large Document Processing

Strategies to handle documents exceeding LLM context window:
1. RecursiveCharacterTextSplitter - semantic-aware chunking (paragraph → sentence → word)
2. Map-Reduce - process chunks independently, then combine (parallelizable)
3. Hierarchical Summarization - summarize chunks first, then process summary
"""

import os
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass

# Try LangChain text splitters - use fallback if not installed
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    HAS_LANGCHAIN_SPLITTER = True
except ImportError:
    HAS_LANGCHAIN_SPLITTER = False


# ~1 char ≈ 0.25 tokens (rough). Gemini 2.5 Flash has 1M tokens, but we use conservative
# chunk size for: (1) quality/focus, (2) fallback for other models, (3) cost
DEFAULT_CHUNK_SIZE = 12000      # ~3000 tokens per chunk - fits comfortably
DEFAULT_CHUNK_OVERLAP = 600     # Overlap to preserve context across boundaries
MAX_DOC_CHARS = 80000          # ~20k tokens - if doc exceeds this, use chunking


@dataclass
class ChunkConfig:
    """Configuration for document chunking"""
    chunk_size: int = DEFAULT_CHUNK_SIZE
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    max_doc_chars: int = MAX_DOC_CHARS
    separators: Optional[List[str]] = None  # Custom: ["\n\n\n", "\n\n", "\n", ". ", " ", ""]


def _simple_split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Fallback splitter when langchain-text-splitters not available.
    Splits by paragraphs first, then by sentences.
    """
    chunks = []
    # Try splitting by double newlines (paragraphs)
    paragraphs = re.split(r'\n\s*\n', text)
    
    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        test_chunk = current_chunk + ("\n\n" if current_chunk else "") + para
        if len(test_chunk) <= chunk_size:
            current_chunk = test_chunk
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If single paragraph is too long, split by sentences
            if len(para) > chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sent in sentences:
                    if len(current_chunk) + len(sent) + 1 > chunk_size and current_chunk:
                        chunks.append(current_chunk)
                        # Overlap: keep last overlap chars
                        overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                        current_chunk = overlap_text + " " + sent
                    else:
                        current_chunk = current_chunk + (" " if current_chunk else "") + sent
            else:
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + "\n\n" + para
    
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


def split_document(text: str, config: Optional[ChunkConfig] = None) -> List[str]:
    """
    Split document into chunks. Uses RecursiveCharacterTextSplitter if available,
    otherwise fallback to simple paragraph/sentence splitter.
    
    Returns:
        List of text chunks, each within chunk_size
    """
    cfg = config or ChunkConfig()
    
    if not text or not text.strip():
        return []
    
    # If document fits in one chunk, return as-is (no unnecessary splitting)
    if len(text) <= cfg.max_doc_chars:
        return [text]
    
    if HAS_LANGCHAIN_SPLITTER:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=cfg.chunk_size,
            chunk_overlap=cfg.chunk_overlap,
            length_function=len,
            separators=cfg.separators or ["\n\n\n", "\n\n", "\n", ". ", " ", ""],
            strip_whitespace=True,
        )
        return splitter.split_text(text)
    
    return _simple_split_text(text, cfg.chunk_size, cfg.chunk_overlap)


def needs_chunking(text: str, max_chars: int = MAX_DOC_CHARS) -> bool:
    """Check if document exceeds safe processing size"""
    return len(text) > max_chars


def prepare_document_for_model(
    text: str,
    config: Optional[ChunkConfig] = None,
) -> Tuple[str, bool]:
    """
    Prepare document for model consumption.
    - If small enough: return full text
    - If too large: use Map-Reduce compatible format (chunks with headers for downstream processing)
    
    Returns:
        (processed_text, used_chunking)
    """
    if not needs_chunking(text, (config or ChunkConfig()).max_doc_chars):
        return text, False
    
    chunks = split_document(text, config)
    # Format chunks for Map-Reduce: each chunk labeled for downstream "map" step
    labeled = []
    for i, c in enumerate(chunks, 1):
        labeled.append(f"--- DOCUMENT PART {i}/{len(chunks)} ---\n{c}\n")
    return "\n".join(labeled), True


# ============== Map-Reduce Helpers ==============
# IMPORTANT: Prompts designed to PRESERVE key content from source document.
# The course agent uses this as PRIMARY source; external knowledge only fills gaps.

MAP_SUMMARY_PROMPT = """Extract and preserve ALL KEY CONTENT from this document section. The output will be the PRIMARY source for course creation - do NOT omit important details.

**MUST PRESERVE (verbatim or near-verbatim):**
- Definitions, terminology, and technical terms
- Key concepts, principles, and facts
- Important examples (keep substance, can condense wording)
- Chapter/section titles and structure
- Procedures, steps, numbered lists
- Formulas, equations, or specific data if present

**Output format:**
- Structured hierarchy (headings reflect document structure)
- Keep exact definitions and key phrases - these must appear in the final course
- Condense verbose explanations but retain ALL unique information
- Do NOT add new content - only extract from the source
- Do NOT create a course outline - only preserve document content for downstream use

DOCUMENT SECTION:
{chunk_content}
"""

REDUCE_COMBINE_PROMPT = """Merge these document section extractions into ONE cohesive document. This will be the PRIMARY source for course creation.

**CRITICAL - PRESERVE ALL KEY CONTENT:**
- Every unique definition, term, concept, and fact from all sections
- Maintain topic hierarchy and structure
- Remove only exact duplicates (same point repeated)
- Do NOT drop any section's unique information
- Order content logically (follow document flow)
- Output: complete merged document that contains ALL important content - the course agent will use this as the main source and supplement with external knowledge only where needed

SECTION EXTRACTIONS:
{summaries}
"""


def get_map_prompt_for_chunk(chunk: str) -> str:
    """Prompt template for Map phase - extract key info from each chunk"""
    return MAP_SUMMARY_PROMPT.format(chunk_content=chunk)


def get_reduce_prompt(summaries: List[str]) -> str:
    """Prompt template for Reduce phase - combine chunk summaries"""
    combined = "\n\n--- NEXT SECTION ---\n\n".join(summaries)
    return REDUCE_COMBINE_PROMPT.format(summaries=combined)


# ============== Map-Reduce Preprocessing (for large docs) ==============

async def map_reduce_compress_document(
    text: str,
    llm_invoke_fn,  # async fn(prompt: str) -> str
    config: Optional[ChunkConfig] = None,
    progress_callback=None,
) -> str:
    """
    Compress long document via Map-Reduce for seamless model processing.
    
    1. Split doc into chunks
    2. MAP: Each chunk → LLM extracts key content/structure (preserves educational value)
    3. REDUCE: Combine summaries → single coherent document under context limit
    
    llm_invoke_fn: async (prompt: str) -> str - e.g. gemini invoke
    progress_callback: optional (message: str, percent: int) for UI updates
    """
    cfg = config or ChunkConfig()
    if not needs_chunking(text, cfg.max_doc_chars):
        return text
    
    chunks = split_document(text, cfg)
    n = len(chunks)
    
    # MAP phase
    summaries = []
    for i, chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(f"Analyzing document section {i+1}/{n}...", 20 + int(40 * (i + 1) / n))
        prompt = get_map_prompt_for_chunk(chunk)
        summary = await llm_invoke_fn(prompt)
        summaries.append(summary.strip())
    
    # REDUCE phase
    if progress_callback:
        progress_callback("Combining document sections...", 65)
    
    combined = "\n\n--- SECTION ---\n\n".join(summaries)
    
    # If combined still too long, run reduce through LLM
    if len(combined) > cfg.max_doc_chars:
        reduce_prompt = get_reduce_prompt(summaries)
        combined = await llm_invoke_fn(reduce_prompt)
    
    if progress_callback:
        progress_callback("Ready for course generation", 75)
    
    return combined.strip()
