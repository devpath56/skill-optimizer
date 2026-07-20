#!/usr/bin/env python3
"""
ingest.py — make an ingested source RETRIEVABLE. The second step after PDF->text extraction: turn the
normalized book text into a structured, cited chunk index (JSONL) the loop can retrieve from precisely.

Why JSONL chunks, not markdown: the consumer is a retrieval loop + a verifier, not a human. One record
per page-chunk with {page, chapter, frontmatter, text} means retrieval returns a COHERENT, CITABLE unit
("APOSD Ch 10, p.84") instead of an arbitrary char-window from a blob, and skips front-matter/TOC by a
flag instead of the brittle digit-density heuristic. Deterministic — regex on the PAGE/Chapter markers,
no model — and the `text` field stays verbatim, so the fidelity checks (S8/S12/S15) still grep it.

The index is a DERIVED artifact of the licensed source, so it is gitignored (copyright), like
book.norm.txt. Rebuild it whenever the source changes.

  python3 engine/ingest.py cartridges/<name>     # build source/book.index.jsonl from book.norm.txt

Exit: 0 built · 6 source absent.
"""
import json
import os
import re
import sys

PAGE = re.compile(r"=====\s*PAGE\s+(\d+)\s*=====")
CHAP = re.compile(r"Chapter\s+(\d+)\s+([A-Z][A-Za-z][\w\s\-\(\)’'&]{2,48}?)(?=\s+\d|\s+[A-Z][a-z]+\s+[a-z])")


def ingest(text):
    """Deterministic page-chunking. Returns a list of {id, page, chapter, chapter_title, frontmatter, text}."""
    # front-matter = every page before "Chapter 1 <Title>" (cover, copyright, Contents, Preface)
    fm = re.search(r"=====\s*PAGE\s+(\d+)\s*=====[^=]*?Chapter\s+1\s+[A-Z]", text)
    first_content_page = int(fm.group(1)) if fm else 0
    parts = PAGE.split(text)  # [pre, num, body, num, body, ...]
    chunks, cur_ch, cur_title = [], None, None
    for i in range(1, len(parts) - 1, 2):
        page = int(parts[i])
        body = " ".join(parts[i + 1].split())
        cm = CHAP.search(body)
        if cm:
            cur_ch, cur_title = int(cm.group(1)), cm.group(2).strip()
        chunks.append({
            "id": f"page-{page}", "page": page, "chapter": cur_ch, "chapter_title": cur_title,
            "frontmatter": page < first_content_page, "text": body,
        })
    return chunks


def build(cart):
    """Build source/book.index.jsonl from the licensed source text. Returns the chunk list, or None if
    the source is absent. Callable as a pipeline step (the loop invokes it once a source is present)."""
    src = os.path.join(cart, "source", "book.norm.txt")
    if not os.path.exists(src):
        return None
    chunks = ingest(open(src, encoding="utf-8", errors="ignore").read())
    out = os.path.join(cart, "source", "book.index.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c) + "\n")
    return chunks


def main(cart):
    chunks = build(cart)
    if chunks is None:
        print("ingest: source absent (source/book.norm.txt) — supply the licensed book text first (see README).")
        sys.exit(6)
    content = [c for c in chunks if not c["frontmatter"]]
    print(f"ingest: {len(chunks)} page-chunks -> {os.path.relpath(out, cart)}  "
          f"({len(chunks) - len(content)} front-matter/TOC pre-filtered, {len(content)} content)")
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1])
