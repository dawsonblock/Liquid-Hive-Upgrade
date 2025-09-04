from __future__ import annotations


def chunk(text: str, meta: dict, max_len: int = 900, overlap: int = 120) -> list[dict]:
    chunks = []
    i = 0
    while i < len(text):
        end = min(i + max_len, len(text))
        chunks.append({"chunk_id": f"sec_{len(chunks)}", "text": text[i:end], "meta": meta})
        if end == len(text):
            break
        i = max(0, end - overlap)
    return chunks
