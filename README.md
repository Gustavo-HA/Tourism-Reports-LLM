# The Voice of the Tourist
## Generation of Tourism Intelligence Reports for Pueblos Mágicos using Large Language Models

This repository contains the implementation of a project focused on generating strategic tourism intelligence reports ("Briefings de Competitividad Estratégica") for México's Pueblos Mágicos by analyzing TripAdvisor reviews with LLMs and a RAG system.

## What are Pueblos Mágicos?

Pueblos Mágicos (Magical Towns) is a tourism program by the Mexican government that recognizes towns throughout México that offer visitors a "magical" experience due to their natural beauty, cultural richness, or historical significance.

## Project Overview

The system transforms scattered tourist reviews into structured intelligence for tourism authorities. Given a Pueblo Mágico, it:

1. Retrieves relevant TripAdvisor reviews from a ChromaDB vector store
2. Extracts structured opportunity insights per business type (Hotel, Restaurant, Attractive) via a parallel Map-Reduce LangGraph workflow
3. Synthesizes and consolidates findings into a strategic briefing
4. Validates the report against the original evidence through a self-correction audit loop
5. Exposes the result via an interactive Streamlit UI with a RAG-backed chat

## System Architecture

### Opportunity Workflow

Located in `voz_turista/application/workflow/`. Uses LangGraph with a Map-Reduce pattern, a self-correction audit loop, and an interactive chat mode.

**Report Generation Graph**:

```
START
  └─> Retrieve reviews by business type
        └─> [parallel] Extract insights  (chunks, per business type)
              └─> Synthezise for report
                    └─> Consolidate the report
                          └─> Audit the report
                                ├─ APPROVED ──> END
                                └─ REJECTED ─> Consolidate again  (up to N iterations)
```

**Chat Graph**:

```
START -> Parse the user query (to vector DB) -> Execute query -> Generate response -> END
```

A **Session** consists on:
- Running the report graph, stores the consolidated report
- Running the chat graph with report context, maintains message history
- An option to return a formatted text summary of the report
- An option to reset the chat message history

### Web Application

A two-process web stack located in `app/`:

* The API created with FastAPI.
* The frontend created with Streamlit.

The FastAPI backend manages stateful sessions (create → generate → chat) and exposes the following endpoints:

```
GET  /api/pueblos                          — list available Pueblos Mágicos
POST /api/sessions                         — create a new analysis session
POST /api/sessions/{id}/generate           — run report generation
GET  /api/sessions/{id}                    — get session status
POST /api/sessions/{id}/chat               — send a chat message
POST /api/sessions/{id}/clear-chat         — reset chat history
DEL  /api/sessions/{id}                    — delete session
```

### Consolidated Report Structure

Each report contains:

1. **Executive Summary** — destination overview and competitive position
2. **Scorecard de Eficiencia Turística** — 1–10 scores for infraestructura, servicios, atractivos (each with justification)
3. **Diagnóstico de Brechas** — underutilized resources from public or private failures
4. **Hoja de Ruta** — prioritized actions split into inversión pública vs capacitación privada
5. **Oportunidades Transversales** — cross-cutting patterns across business types
6. **Detalle por Tipo de Negocio** — per-type summaries (Hotel, Restaurant, Attractive)

### Core Modules

| Layer | Module | Purpose |
|---|---|---|
| Domain | `voz_turista/domain/schemas.py` | Pydantic models for all workflow data |
| Domain | `voz_turista/domain/prompts/templates.py` | LLM prompt templates (legacy) |
| Infrastructure | `voz_turista/infrastructure/llm_providers/` | Abstract `LLMProvider` + `LiteLLMProvider` |
| Infrastructure | `voz_turista/infrastructure/database/chroma_client.py` | ChromaDB wrapper with HNSW cosine similarity |
| Application | `voz_turista/application/workflow/` | Primary opportunity workflow (nodes, state, graph, session) |

## Technology Stack

- **LangGraph** — stateful multi-step workflow orchestration (Map-Reduce + conditional edges)
- **LiteLLM** — provider-agnostic LLM access (Gemini, OpenAI, Anthropic, Groq, …)
- **ChromaDB** — local vector database for review storage and semantic retrieval
- **sentence-transformers** — Spanish-language embedding models
- **FastAPI** — async REST backend with session management
- **Streamlit** — interactive web frontend
- **MLflow** — experiment tracking
- **DVC** — data versioning (notebooks, mlruns, vector DB)
- **uv** — dependency management and virtual environment

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone the repo and install dependencies
git clone https://github.com/Gustavo-HA/Tourism-Reports-LLM.git
cd Tourism-Reports-LLM
uv sync
```

### Environment Setup

Create a `.env` file in the project root:

```dotenv
# LLM provider key (at least one required)
GEMINI_API_KEY=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GROQ_API_KEY=...

# Model configuration
LLM_MODEL=gemini/gemini-2.5-flash        # LiteLLM model identifier
LLM_TEMPERATURE=0.0                       # optional, defaults to 0.0
EMBEDDING_MODEL=hiiamsid/sentence_similarity_spanish_es

# Vector database
VECTOR_DB_PATH=data/chromadb/restmex_sss_cs200_ov50/
VECTOR_DB_COLLECTION=restmex_sss_cs200_ov50

# Optional: two-stage retrieval reranker
RERANKER_MODEL=cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
```

### Data

Review data is versioned with DVC. Download from the configured remote:

```bash
make sync_data_down
# or: uv run dvc pull
```

### Running the Application

```bash
# Start the FastAPI backend (port 8000)
make api

# In a separate terminal, start the Streamlit frontend (port 8501)
make frontend
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

### Running from the CLI

```bash
# Run the opportunity workflow directly (primary)
python scripts/test_opportunity_workflow.py Isla_Mujeres
```

## Available Make Commands

```
make requirements     Install/update dependencies (uv sync)
make api              Run FastAPI backend server
make frontend         Run Streamlit frontend
make lint             Lint code with ruff
make format           Format code with ruff
make sync_data_down   Download data from DVC remote
make sync_data_up     Upload data to DVC remote
make clean            Delete compiled Python files
```

## Project Structure

```
Tourism-Reports-LLM/
├── app/
│   ├── api.py                  # FastAPI REST backend
│   └── frontend.py             # Streamlit web UI
├── data/                       # DVC-managed data (reviews, vector DB)
├── mlruns/                     # MLflow experiment tracking (DVC-managed)
├── notebooks/                  # Exploration notebooks (DVC-managed)
├── scripts/
│   └── test_opportunity_workflow.py
├── voz_turista/
│   ├── application/
│   │   └── workflow/           # Primary opportunity workflow
│   │       ├── graph.py        # LangGraph workflow definitions
│   │       ├── nodes.py        # Workflow node implementations
│   │       ├── prompts.py      # Prompt templates
│   │       ├── session.py      # OpportunitySession orchestrator
│   │       └── state.py        # TypedDict state definitions
│   ├── domain/
│   │   ├── schemas.py          # Pydantic data models
│   │   └── prompts/templates.py
│   ├── infrastructure/
│   │   ├── database/
│   │   │   └── chroma_client.py
│   │   └── llm_providers/
│   │       ├── base.py
│   │       ├── litellm_provider.py
│   │       └── google_provider.py
│   ├── tools/
│   └── config.py
├── pyproject.toml
├── Makefile
└── CLAUDE.md
```

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- REST-MEX event for the review data.
