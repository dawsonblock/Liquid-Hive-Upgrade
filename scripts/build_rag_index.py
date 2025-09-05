"""Reproducible FAISS index generation for RAG system."""

import argparse
import os
import sys
import time
import hashlib
from pathlib import Path
from typing import List, Iterator
import structlog

logger = structlog.get_logger(__name__)

def lazy_imports():
    """Import heavy dependencies only when needed."""
    try:
        import faiss
        import numpy as np
        return faiss, np
    except ImportError as e:
        logger.error("Missing dependencies for FAISS build", error=str(e))
        print(f"[RAG] Missing dependencies for FAISS build: {e}", file=sys.stderr)
        print("Install with: pip install faiss-cpu numpy", file=sys.stderr)
        sys.exit(2)

def iter_docs(src: Path) -> Iterator[Path]:
    """Iterate through documentation files."""
    for p in src.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".txt", ".md", ".rst", ".json"}:
            yield p

def read_document(file_path: Path, max_size: int = 1024 * 1024) -> str:
    """Read document content with size limits."""
    try:
        if file_path.stat().st_size > max_size:
            logger.warning("File too large, skipping", 
                          file=str(file_path), 
                          size=file_path.stat().st_size)
            return ""
        
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        
        # Basic content validation
        if len(content.strip()) < 50:  # Skip very short files
            return ""
        
        return content
        
    except Exception as e:
        logger.warning("Failed to read file", file=str(file_path), error=str(e))
        return ""

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks for better retrieval."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings in the last 100 characters
            search_start = max(end - 100, start)
            sentence_end = max(
                text.rfind('.', search_start, end),
                text.rfind('!', search_start, end),
                text.rfind('?', search_start, end)
            )
            
            if sentence_end > start:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = max(start + 1, end - overlap)
    
    return chunks

def main():
    """Main function for RAG index building."""
    ap = argparse.ArgumentParser(description="Build FAISS index for RAG system")
    ap.add_argument("--src", default="data/ingest", help="Source text docs directory")
    ap.add_argument("--out", default="rag_index/faiss_index.bin", help="Output FAISS index file")
    ap.add_argument("--chunk-size", type=int, default=1000, help="Text chunk size")
    ap.add_argument("--chunk-overlap", type=int, default=200, help="Chunk overlap size")
    ap.add_argument("--min-docs", type=int, default=1, help="Minimum documents required")
    ap.add_argument("--force", action="store_true", help="Force rebuild even if output exists")
    
    args = ap.parse_args()
    
    src = Path(args.src)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if rebuild needed
    if out.exists() and not args.force:
        logger.info("Index already exists, use --force to rebuild", output=str(out))
        print(f"[RAG] Index already exists: {out}")
        print(f"[RAG] Use --force to rebuild or delete the file manually")
        return 0
    
    # Find source documents
    files = list(iter_docs(src))
    if len(files) < args.min_docs:
        logger.warning("Insufficient documents found", 
                      found=len(files), 
                      required=args.min_docs,
                      source=str(src))
        print(f"[RAG] Only {len(files)} docs found in {src} (need {args.min_docs})")
        return 1
    
    logger.info("Starting RAG index build",
               source=str(src),
               output=str(out),
               documents=len(files),
               chunk_size=args.chunk_size)
    
    # Import heavy dependencies
    faiss, np = lazy_imports()
    
    # Try to get embedder
    try:
        from src.hivemind.embedding.embedder import embed_batch, get_embedding_dimension
        embedding_dim = get_embedding_dimension()
    except ImportError:
        logger.error("Embedder not available")
        print("[RAG] Embedder not available - install embedding dependencies")
        return 2
    
    # Process documents and create chunks
    all_chunks = []
    doc_metadata = []
    
    for file_path in files:
        logger.debug("Processing document", file=str(file_path))
        
        content = read_document(file_path)
        if not content:
            continue
        
        # Create chunks from document
        chunks = chunk_text(content, args.chunk_size, args.chunk_overlap)
        
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            doc_metadata.append({
                "source_file": str(file_path.relative_to(src)),
                "chunk_index": i,
                "total_chunks": len(chunks),
                "doc_hash": hashlib.md5(content.encode()).hexdigest()[:8],
                "chunk_size": len(chunk)
            })
    
    if not all_chunks:
        logger.error("No valid text content found")
        print(f"[RAG] No readable text content found in {src}")
        return 1
    
    logger.info("Text processing completed",
               total_chunks=len(all_chunks),
               avg_chunk_size=sum(len(c) for c in all_chunks) // len(all_chunks))
    
    print(f"[RAG] Processing {len(all_chunks)} chunks from {len(files)} documents...")
    
    # Generate embeddings
    try:
        start_time = time.time()
        embeddings = embed_batch(all_chunks, batch_size=50)
        embedding_time = time.time() - start_time
        
        logger.info("Embeddings generated",
                   count=len(embeddings),
                   dimension=len(embeddings[0]) if embeddings else 0,
                   time_seconds=embedding_time)
        
        print(f"[RAG] Generated {len(embeddings)} embeddings in {embedding_time:.2f}s")
        
    except Exception as e:
        logger.error("Embedding generation failed", error=str(e))
        print(f"[RAG] Embedding generation failed: {e}")
        return 3
    
    # Convert to numpy array and validate
    try:
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        if embeddings_array.shape[1] != embedding_dim:
            logger.error("Embedding dimension mismatch",
                        expected=embedding_dim,
                        actual=embeddings_array.shape[1])
            return 4
        
        # Normalize embeddings for cosine similarity
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        embeddings_array = embeddings_array / np.maximum(norms, 1e-8)
        
    except Exception as e:
        logger.error("Embedding array processing failed", error=str(e))
        print(f"[RAG] Array processing failed: {e}")
        return 4
    
    # Build FAISS index
    try:
        start_time = time.time()
        
        # Use IndexFlatIP for cosine similarity (inner product on normalized vectors)
        index = faiss.IndexFlatIP(embedding_dim)
        
        # Add vectors to index
        index.add(embeddings_array)
        
        index_time = time.time() - start_time
        
        logger.info("FAISS index built",
                   vectors=index.ntotal,
                   dimension=embedding_dim,
                   time_seconds=index_time)
        
        print(f"[RAG] Built FAISS index with {index.ntotal} vectors")
        
    except Exception as e:
        logger.error("FAISS index construction failed", error=str(e))
        print(f"[RAG] FAISS index build failed: {e}")
        return 5
    
    # Save index to disk
    try:
        faiss.write_index(index, str(out))
        
        # Save metadata
        metadata_file = out.with_suffix('.json')
        import json
        
        metadata = {
            "created_at": time.time(),
            "source_directory": str(src),
            "documents_processed": len(files),
            "chunks_created": len(all_chunks),
            "embedding_dimension": embedding_dim,
            "index_type": "IndexFlatIP",
            "chunk_size": args.chunk_size,
            "chunk_overlap": args.chunk_overlap,
            "build_stats": {
                "embedding_time_seconds": embedding_time,
                "index_time_seconds": index_time,
                "total_time_seconds": time.time() - start_time
            },
            "chunks_metadata": doc_metadata
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("Index saved successfully",
                   index_file=str(out),
                   metadata_file=str(metadata_file),
                   size_mb=out.stat().st_size / (1024 * 1024))
        
        print(f"[RAG] Index saved to: {out}")
        print(f"[RAG] Metadata saved to: {metadata_file}")
        print(f"[RAG] Index size: {out.stat().st_size / (1024 * 1024):.2f} MB")
        print(f"[RAG] Total vectors: {index.ntotal}")
        print(f"[RAG] Build completed successfully! ✅")
        
        return 0
        
    except Exception as e:
        logger.error("Failed to save index", error=str(e))
        print(f"[RAG] Failed to save index: {e}")
        return 6

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)