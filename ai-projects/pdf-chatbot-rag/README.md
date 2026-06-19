# PDF Chatbot with RAG (Retrieval-Augmented Generation)

A command-line chatbot that lets you have a conversation with any PDF document. Built using OpenAI embeddings and GPT-4o-mini, it finds the most relevant sections of your PDF before answering each question — no hallucination from thin air.

## How It Works

```
PDF → Extract Text → Chunk → Embed (text-embedding-3-small)
                                        ↓
Question → Embed → Cosine Similarity Search → Top-K Chunks
                                        ↓
              GPT-4o-mini (question + context) → Answer
```

1. Extracts and chunks the PDF text into 500-word overlapping segments
2. Embeds every chunk using OpenAI's `text-embedding-3-small`
3. On each question, embeds the query and finds the top-4 most similar chunks
4. Feeds those chunks as context to GPT-4o-mini to generate a grounded answer
5. Maintains multi-turn conversation history for follow-up questions
6. Caches embeddings locally so you don't re-embed the same PDF twice

## Setup

```bash
# 1. Clone / navigate to this folder
cd pdf-chatbot-rag

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your API key
cp .env.example .env
# Edit .env and paste your OpenAI API key
```

## Usage

```bash
python chatbot.py path/to/your/document.pdf
```

**Example session:**
```
=== PDF Chatbot (RAG) ===
Loading: research_paper.pdf

  Extracting text from PDF...
  Chunking text (8432 words)...
  Created 18 chunks. Generating embeddings...
  Embeddings cached for future use.

Ready! 18 chunks indexed from your PDF.
Type your question below. Type 'exit' to quit.

You: What is the main contribution of this paper?
Assistant: The paper's main contribution is ...

You: How does it compare to prior work?
Assistant: Compared to prior approaches, ...

You: exit
```

## Run Tests

```bash
python test_chatbot.py
```

Tests cover chunking correctness, cosine similarity math, and top-k retrieval logic — no API key needed.

## Tech Stack

| Component | Technology |
|---|---|
| LLM | OpenAI GPT-4o-mini |
| Embeddings | text-embedding-3-small |
| PDF Parsing | PyPDF2 |
| Vector Search | Cosine similarity (pure Python) |
| Caching | Local JSON cache |

## Project Structure

```
pdf-chatbot-rag/
├── chatbot.py          # Main application
├── test_chatbot.py     # Sanity tests (no API key needed)
├── requirements.txt
├── .env.example
└── README.md
```

## Notes

- Works best with text-based PDFs. Scanned/image PDFs require OCR preprocessing.
- Embeddings are cached as `<filename>.cache.json` — delete it to re-index.
- Conversation history is kept in-memory (resets on restart).
