# Markdown Converter

A **single-file, zero-install** Markdown → PDF / Word converter. One self-contained HTML page (~60 KB) — no dependencies, no build step, no internet access required, nothing to install.

Built for the classic SE problem: you have a Markdown study guide, runbook, or one-pager on a **locked-down corporate PC** and need to send someone a presentable document. No admin rights, no pandoc, no problem.

## 🔒 Privacy

**All conversion happens client-side in your browser.** Even when the page is served from another machine, your document never leaves your PC — the server only delivers the page itself. Nothing is uploaded anywhere. Safe for internal/confidential content.

## 🚀 Three ways to use it

### 1. Double-click (simplest)
Download [`index.html`](index.html), double-click it, done. Works from a USB stick, a file share, or your Downloads folder.

### 2. Host on your LAN
Serve it to teammates from any box with Python:

```
python -m http.server 8080 --bind 0.0.0.0
```

Run that from this folder, then everyone browses to `http://<your-ip>:8080`.

### 3. Any static host
It's one static file — drop it on any internal web server, S3 bucket, or intranet page.

## ✨ Features

- **Drag & drop** a `.md` file anywhere on the page, use the file picker, or paste Markdown for live rendering
- **Print / Save as PDF** — renders via the browser's print-to-PDF with print-optimized styles (page-break avoidance for tables and code blocks)
- **Download as Word (.doc)** — one click, opens in Microsoft Word with styled headings, tables, code blocks, and blockquotes
- **GitHub-style rendering** — full GFM support: tables, task lists, fenced code blocks, strikethrough

## 💡 Tips

- **PDF:** in the print dialog, expand *More settings* and enable **Background graphics** so code blocks keep their shading.
- **Word:** the `.doc` output is Word-compatible HTML — it opens and re-saves cleanly in Word. If you need native `.docx` fidelity for heavy re-editing, run the output through `pandoc` afterward.
- The output document is named after your input file automatically.

## 🔧 Under the hood

Everything is embedded in the one file:

| Component | Purpose | License |
|-----------|---------|---------|
| [marked](https://github.com/markedjs/marked) v12 | Markdown → HTML parsing | MIT |
| [github-markdown-css](https://github.com/sindresorhus/github-markdown-css) v5 | GitHub-style rendering | MIT |

Word export uses the Office HTML namespace wrapper (`application/msword`), so no server-side conversion is needed.
