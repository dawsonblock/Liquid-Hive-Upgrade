from __future__ import annotations
from bs4 import BeautifulSoup
from readability import Document


def html_to_text(html: str) -> tuple[str, str]:
    try:
        doc = Document(html)
        title = doc.short_title() or ""
        summary_html = doc.summary(html_partial=True)
        soup = BeautifulSoup(summary_html, "lxml")
        text = soup.get_text(separator=" ", strip=True)
        return title, text
    except Exception:
        soup = BeautifulSoup(html or "", "lxml")
        title = soup.title.string.strip() if (soup.title and soup.title.string) else ""
        text = soup.get_text(separator=" ", strip=True)
        return title, text
