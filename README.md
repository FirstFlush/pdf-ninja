<p align="center">
  <img src="https://i.imgur.com/xqucH5L.png" width="300" alt="PDF Ninja logo">
</p>

# 🥷 PDF-Ninja

**PDF-Ninja** is a modular, Python-based PDF parsing **library** built for **AI and data extraction pipelines** — especially **RAG (Retrieval-Augmented Generation)** systems.

It’s designed for cases where PDFs aren’t just blobs of text, but complex documents with **tables, figures, images, metadata, and structured text** that need to be extracted cleanly and consistently.


## 💡 Why It Exists

Tools like `pdfplumber`, `camelot`, and `tabula` each excel at different parts of the PDF parsing problem — text extraction, table recognition, and layout analysis.  
PDF-Ninja brings them together into a single orchestration layer that:

- Extracts **text, tables, images, figures, and metadata** in one pass  
- Preserves **page structure and element order** via bounding boxes  
- Produces a **standardized JSON-ready object model**  
- Provides a foundation for **embedding, chunking, and vectorization** in RAG pipelines

It’s purpose-built for **machine understanding** of real-world PDFs such as:
- Financial filings (10-K, 10-Q, MD&A)
- Technical reports
- Scientific papers
- Corporate disclosures


## ⚙️ Core Concepts

### 🧩 Extractors
Each content type (text, table, image, figure, metadata) has its own extractor.  
They run independently but output a common format of `PdfElement` objects.

### 🧱 Builders
Builders assemble the extracted elements into higher-level data structures:
- `PdfPage` — ordered list of elements for a single page  
- `ParsedPdf` — the fully structured document, metadata included

### 🧠 Contexts
`PdfContext` manages shared access to backend engines:
- `pdfplumber` for text and layout  
- `camelot` and `tabula` for tables  
- `pypdf` for metadata and encryption handling  


## 🧰 Tech Stack

| Component | Purpose |
|------------|----------|
| **pdfplumber** | text and layout extraction |
| **camelot-py** | ruled-line table detection |
| **tabula-py** | whitespace-based table parsing |
| **pypdf** | metadata, encryption, PDF structure |
| **dataclasses** | clean internal schema for all content |
| **typing / pathlib / logging** | modern Python hygiene |


## 📦 Output Schema

A parsed PDF produces a structured object that’s JSON-serializable:

```json
{
  "source": "annual_report_2023.pdf",
  "metadata": { "title": "Annual Report 2023", "page_count": 42 },
  "pages": [
    {
      "page_number": 1,
      "elements": [
        { "type": "text", "order": 0, "content": "Overview...", "bbox": [72, 95, 520, 110] },
        { "type": "table", "order": 1, "rows": [["Mine", "AISC"], ["Cigar Lake", "1.23"]], "bbox": [70, 200, 500, 340] }
      ]
    }
  ]
}
```

This structure is designed to plug directly into **chunking, embedding, and vector storage** pipelines.


## 🚀 Design Goals

- **RAG-focused** — output is embedding-ready  
- **Deterministic structure** — always reproducible and traceable  
- **Extensible** — add new extractors or post-processors easily  
- **Library design** — clean API, no web server or framework dependencies  
- **Human-readable** — clear data model for debugging and analysis  


## 🧭 Project Status

PDF-Ninja is under active development.  
Its first milestone focuses on:
- Stable text + table extraction across varied layouts  
- Page-ordered output suitable for document intelligence pipelines  
- Extensible builder patterns for future extractors (charts, figures, OCR, etc.)
