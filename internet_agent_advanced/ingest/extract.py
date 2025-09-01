from __future__ import annotations
from bs4 import BeautifulSoup
from readability import Document
import trafilatura

def extract_readable(html: str):
    meta = {}
    try:
        doc = Document(html)
        title = doc.short_title()
        summary_html = doc.summary(html_partial=True)
        soup = BeautifulSoup(summary_html, "lxml")
        text = soup.get_text("\n")
        meta["title"] = title
        return text, meta
    except Exception:
        try:
            text = trafilatura.extract(html) or ""
            soup = BeautifulSoup(html, "lxml")
            meta["title"] = soup.title.string.strip() if soup.title and soup.title.string else ""
            return text, meta
        except Exception:
            soup = BeautifulSoup(html or "", "lxml")
            meta["title"] = soup.title.string.strip() if soup.title and soup.title.string else ""
            return soup.get_text("\n"), meta
