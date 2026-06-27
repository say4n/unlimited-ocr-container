#!/usr/bin/env python3
"""Convert Unlimited-OCR / DeepSeek-OCR grounding output to clean Markdown or
layout-preserving HTML.

The model emits blocks shaped like:

    <|det|>{label} [x1, y1, x2, y2]<|/det|>{content}

where {label} is a layout role (text, title, header, footer, table, image,
page_number, ...), the coordinates are normalized to 0-999, and {content} is the
recognized text (tables arrive as embedded HTML <table>).

Usage:
    # one or more per-page .md files, or a directory containing them:
    grounding_to_markdown.py outputs/ --md clean.md --html layout.html
    grounding_to_markdown.py doc_page_0001.md doc_page_0002.md --md -   # stdout
    grounding_to_markdown.py outputs/ --md clean.md --gfm                # HTML tables -> GFM
"""
import argparse
import glob
import html as _html
import os
import re
import sys

BLOCK_RE = re.compile(
    r"<\|det\|>\s*([a-z_]+)\s*\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\s*<\|/det\|>(.*?)"
    r"(?=<\|det\|>|\Z)",
    re.S,
)
PAGE_NUM_RE = re.compile(r"page[_-]?(\d+)", re.I)


def parse_blocks(text):
    blocks = []
    for m in BLOCK_RE.finditer(text):
        x1, y1, x2, y2 = (int(m.group(i)) for i in range(2, 6))
        blocks.append(
            dict(label=m.group(1), box=(x1, y1, x2, y2), content=m.group(6).strip())
        )
    return blocks


def reading_order(blocks):
    # top-to-bottom in coarse 25-unit bands, then left-to-right within a band
    return sorted(blocks, key=lambda b: (b["box"][1] // 25, b["box"][0]))


def html_table_to_gfm(table_html):
    """Best-effort conversion of a simple <table> to GitHub-Flavored Markdown.
    Falls back to the raw HTML when the table uses colspan/rowspan (GFM can't
    represent spans)."""
    if re.search(r"colspan|rowspan", table_html, re.I):
        return table_html  # GFM cannot express spans; keep HTML
    rows = re.findall(r"<tr.*?>(.*?)</tr>", table_html, re.S | re.I)
    if not rows:
        return table_html
    grid = []
    for r in rows:
        cells = re.findall(r"<t[dh].*?>(.*?)</t[dh]>", r, re.S | re.I)
        grid.append([re.sub(r"\s+", " ", _html.unescape(c)).strip() for c in cells])
    width = max(len(r) for r in grid)
    grid = [r + [""] * (width - len(r)) for r in grid]
    out = ["| " + " | ".join(grid[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
    for r in grid[1:]:
        out.append("| " + " | ".join(c.replace("|", "\\|") for c in r) + " |")
    return "\n".join(out)


def load_pages(inputs):
    """inputs: list of files and/or directories. Returns [(pageno, blocks), ...]."""
    files = []
    for item in inputs:
        if os.path.isdir(item):
            files += sorted(glob.glob(os.path.join(item, "*_page_*.md"))) or sorted(
                glob.glob(os.path.join(item, "*.md"))
            )
        else:
            files.append(item)
    pages = []
    for i, f in enumerate(files, 1):
        m = PAGE_NUM_RE.search(os.path.basename(f))
        pageno = int(m.group(1)) if m else i
        with open(f, encoding="utf-8") as fh:
            pages.append((pageno, parse_blocks(fh.read())))
    pages.sort(key=lambda p: p[0])
    return pages


def to_markdown(pages, gfm=False):
    out = []
    for pageno, blocks in pages:
        out.append(f"\n\n---\n\n<!-- página {pageno} -->\n")
        para = []

        def flush():
            if para:
                out.append(" ".join(para))
                para.clear()

        for b in reading_order(blocks):
            c, lab = b["content"], b["label"]
            if lab == "title":
                flush()
                out.append(f"\n## {c}\n")
            elif lab in ("header", "footer", "page_number"):
                continue  # ruído de cabeçalho/rodapé/numeração
            elif lab == "image":
                flush()
                out.append("\n*[imagem/carimbo]*\n")
            elif lab == "table":
                flush()
                out.append("\n" + (html_table_to_gfm(c) if gfm else c) + "\n")
            else:
                # acumula linhas de texto contíguas num parágrafo
                if c.endswith((".", ":", ";", "!", "?")) or len(c) > 80:
                    para.append(c)
                    flush()
                else:
                    para.append(c)
        flush()
    return "\n".join(out).strip() + "\n"


PAGE_W, PAGE_H = 700, 990
COLORS = {"title": "#1a4d80", "header": "#999", "footer": "#999",
          "page_number": "#bbb", "table": "#0a7", "image": "#c33", "text": "#111"}


def to_html(pages):
    parts = ["""<!doctype html><html><head><meta charset="utf-8"><style>
body{background:#666;font-family:Arial,Helvetica,sans-serif;margin:0;padding:1px;}
.page{position:relative;background:#fff;margin:24px auto;box-shadow:0 2px 12px #0008;
      width:%dpx;height:%dpx;overflow:hidden;}
.blk{position:absolute;font-size:11px;line-height:1.15;overflow:hidden;
     border:1px solid #eee;padding:1px 2px;box-sizing:border-box;}
table{border-collapse:collapse;width:100%%;font-size:9px;}
td,th{border:1px solid #999;padding:1px 2px;}
.lab-title{font-weight:bold;}
</style></head><body>""" % (PAGE_W, PAGE_H)]
    for pageno, blocks in pages:
        parts.append(f'<div class="page" title="página {pageno}">')
        for b in blocks:
            x1, y1, x2, y2 = b["box"]
            left, top = x1 / 1000 * PAGE_W, y1 / 1000 * PAGE_H
            w, h = max(4, (x2 - x1) / 1000 * PAGE_W), max(4, (y2 - y1) / 1000 * PAGE_H)
            col = COLORS.get(b["label"], "#111")
            if b["label"] == "table":
                inner = b["content"]
            elif b["label"] == "image":
                inner = '<span style="color:#c33;font-size:8px">[imagem]</span>'
            else:
                inner = _html.escape(b["content"])
            parts.append(
                f'<div class="blk lab-{b["label"]}" style="left:{left:.1f}px;'
                f'top:{top:.1f}px;width:{w:.1f}px;height:{h:.1f}px;color:{col}">'
                f"{inner}</div>"
            )
        parts.append("</div>")
    parts.append("</body></html>")
    return "\n".join(parts)


def _write(path, data):
    if path == "-":
        sys.stdout.write(data)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"wrote {path}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="per-page .md files or a directory")
    ap.add_argument("--md", metavar="OUT", help="write clean Markdown ('-' = stdout)")
    ap.add_argument("--html", metavar="OUT", help="write layout-preserving HTML")
    ap.add_argument("--gfm", action="store_true",
                    help="convert simple HTML tables to GitHub-Flavored Markdown")
    args = ap.parse_args()

    pages = load_pages(args.inputs)
    if not pages:
        print("no grounding blocks found", file=sys.stderr)
        sys.exit(1)

    if not args.md and not args.html:
        args.md = "-"  # default: clean markdown to stdout
    if args.md:
        _write(args.md, to_markdown(pages, gfm=args.gfm))
    if args.html:
        _write(args.html, to_html(pages))


if __name__ == "__main__":
    main()
