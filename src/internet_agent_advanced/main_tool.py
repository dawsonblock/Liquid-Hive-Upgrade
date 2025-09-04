from __future__ import annotations

from .router import route_fetch
from .schemas import FetchResult, ScoredItem
from .search import internet_search as _internet_search
from .trust_filter import is_trusted, score_url


async def internet_fetch(urls: list[str], render_js: bool = False) -> FetchResult:
    results = FetchResult()
    for url in urls:
        try:
            routed = await route_fetch(url, render_js=render_js)
            kind = routed["kind"]
            data = routed["data"]
            if kind == "web_page":
                score = score_url(data.get("url"))
                item = ScoredItem(
                    url=data.get("url"),
                    score=score,
                    title=data.get("title"),
                    content=data.get("content"),
                    meta={
                        "kind": kind,
                        "status": data.get("status"),
                        "mime": data.get("mime"),
                        "rendered": data.get("rendered"),
                        "elapsed_ms": data.get("elapsed_ms"),
                    },
                )
                if data.get("blocked") or data.get("captcha_required"):
                    results.blocked.append(item)
                elif is_trusted(item.url):
                    results.trusted.append(item)
                else:
                    results.unverified.append(item)
            elif kind in ("github_repo", "huggingface_model"):
                url_hint = (
                    data.get("html_url")
                    if kind == "github_repo"
                    else f"https://huggingface.co/{data.get('repo_id')}"
                )
                score = score_url(url_hint)
                content = (
                    data.get("readme") if kind == "github_repo" else str(data.get("model_card"))
                )
                title = data.get("full_name") if kind == "github_repo" else data.get("repo_id")
                item = ScoredItem(
                    url=url_hint,
                    score=score,
                    title=title,
                    content=content,
                    meta={
                        "kind": kind,
                        **{k: v for k, v in data.items() if k not in ("readme", "model_card")},
                    },
                )
                if is_trusted(url_hint):
                    results.trusted.append(item)
                else:
                    results.unverified.append(item)
        except Exception as e:
            results.errors.append({"url": url, "error": repr(e)})
    return results


async def internet_search(query: str, max_results: int = 5) -> FetchResult:
    return await _internet_search(query, max_results=max_results)


# Ingest: extract→chunk→dedup→embed→Qdrant→lineage
from .ingest.chunker import chunk
from .ingest.dedup import content_hash
from .ingest.embedder import embed_texts
from .ingest.extract import extract_readable
from .ingest.indexers import index_qdrant
from .ingest.lineage import store_raw
from .scraper import fetch


async def internet_ingest(url: str, render_js: bool = False) -> dict:
    page = await fetch(url, render_js=render_js)
    html = page.content_html or page.content or ""
    text, meta = extract_readable(page.content_html or "")
    # If readability fails and text empty, fallback to normalized text
    if not text and page.content:
        text = page.content
    h = content_hash(text or html)
    meta = {"title": meta.get("title", ""), "url": page.url, "hash": h}
    chs = chunk(text, meta)
    vecs = await embed_texts([c["text"] for c in chs])
    idx = await index_qdrant(chs, vecs, meta)
    loc = store_raw(page.url, html or "", h)
    return {
        "url": page.url,
        "hash": h,
        "chunks": len(chs),
        "indexed": idx,
        "raw_store": loc,
        "title": meta["title"],
    }
