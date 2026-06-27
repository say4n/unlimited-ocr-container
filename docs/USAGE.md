# Usage: `ocrpdf` + Markdown conversion

This fork adds two helpers on top of the container:

- [`scripts/ocrpdf`](../scripts/ocrpdf) — one-shot wrapper: PDF in, clean Markdown out.
- [`scripts/grounding_to_markdown.py`](../scripts/grounding_to_markdown.py) — converts the
  model's raw layout-grounding output into clean Markdown or layout-preserving HTML.

> The GPU image needs the [`libnuma1` fix](../Dockerfile); without it the SGLang server
> fails to start (`ImportError: libnuma.so.1`).

---

## `ocrpdf`

Runs the container, auto-selects the GPU with the most free VRAM, reuses the model cache,
and prints **clean Markdown to stdout**. Progress goes to stderr, so the Markdown stays clean.

```bash
# put it on PATH (optional)
sudo install scripts/ocrpdf /usr/local/bin/ocrpdf

# basic
ocrpdf documento.pdf > documento.md

# read the PDF from stdin (no temp file needed)
ocrpdf - < documento.pdf > documento.md

# also emit the positioned HTML
ocrpdf documento.pdf --html layout.html > documento.md

# raw model output (keeps the <|det|> grounding tags)
ocrpdf documento.pdf --raw > documento.raw.md
```

### Over SSH (from another machine)

No need to copy the PDF first — stream it through stdin:

```bash
ssh user@host 'ocrpdf -' < documento.pdf > documento.md
ssh user@host 'ocrpdf - --html /tmp/layout.html' < documento.pdf > documento.md
```

### Environment variables

| Variable          | Default                                      | Meaning                              |
|-------------------|----------------------------------------------|--------------------------------------|
| `OCR_IMAGE`       | `ghcr.io/say4n/unlimited-ocr-container:gpu`  | Docker image to run                  |
| `OCR_MODELS`      | `$PWD/models`                                | HuggingFace model cache mount        |
| `OCR_CONVERTER`   | `scripts/grounding_to_markdown.py`           | converter invoked for Markdown       |
| `OCR_CONCURRENCY` | `6`                                          | concurrent requests to SGLang        |
| `OCR_IMAGE_MODE`  | `gundam`                                     | model image mode (`gundam`/`base`)   |

The first run downloads the model (~6 GB) into `OCR_MODELS`; later runs reuse it.

---

## `grounding_to_markdown.py`

Use it directly on per-page `.md` files (the raw container output):

```bash
python3 scripts/grounding_to_markdown.py outputs/ --md clean.md --html layout.html --gfm
```

- `--md <file|->` clean reading-order Markdown (`-` = stdout)
- `--html <file>` HTML that positions every block by its bounding box
- `--gfm` convert simple HTML tables to GitHub-Flavored Markdown tables
  (tables with `colspan`/`rowspan` stay as HTML, which GFM cannot represent)

It drops `header`/`footer`/`page_number` noise, renders `title` blocks as headings,
keeps tables, and marks `image` blocks as `*[imagem/carimbo]*`.

---

## Output format (raw model output)

The model emits *layout grounding*:

```
<|det|>{label} [x1, y1, x2, y2]<|/det|>{content}
```

- `{label}` — block role: `text`, `title`, `header`, `footer`, `table`, `image`, `page_number`
- `[x1,y1,x2,y2]` — bounding box, normalized to **0–999** (x horizontal, y vertical)
- `{content}` — recognized text; **tables arrive as embedded HTML `<table>`**

This is the model's own markup (DeepSeek-OCR / GOT-OCR2 family), not an open standard
such as hOCR, ALTO XML, or PAGE XML.

---

## Notes

- **VRAM / Ollama and friends:** if another process holds all GPU memory, OCR may fail to
  allocate. `ocrpdf` picks the freest GPU, but it still needs a few GB free.
- **Reference performance:** ~31 pages in ~110 s on an RTX 3060 (~250 tokens/s).
