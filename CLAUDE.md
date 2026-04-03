# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tourism intelligence report generation system for México's Pueblos Mágicos using LLMs and RAG. Analyzes TripAdvisor reviews to produce strategic briefings for tourism authorities.

## Commands

```bash
# Install dependencies (uses uv package manager)
make requirements
# or: uv sync

# Lint code
make lint

# Format code
make format

# Download data from DVC storage
make sync_data_down

# Upload data to DVC storage
make sync_data_up

# Run workflow test
python scripts/test_workflow.py
```

## Dependency Management

This project uses [uv](https://docs.astral.sh/uv/) as its package manager. Dependencies are declared in `pyproject.toml` and locked in `uv.lock`. Key commands:
- `uv sync` — install/update all dependencies from the lockfile
- `uv add <package>` — add a new dependency
- `uv remove <package>` — remove a dependency
- `uv run <command>` — run a command within the managed environment

The `make requirements` target wraps `uv sync`.

## Environment Setup

Requires a `.env` file with the API key for your chosen LLM provider. LiteLLM reads keys from standard env vars:
- `GEMINI_API_KEY` - Google Gemini
- `OPENAI_API_KEY` - OpenAI
- `ANTHROPIC_API_KEY` - Anthropic
- `GROQ_API_KEY` - Groq

Default settings in `voz_turista/config.py`:
- LLM: `gemini/gemini-2.5-flash` (litellm model format)
- Embedding model: `hiiamsid/sentence_similarity_spanish_es`
- Vector DB path: `data/vectordb`

To use a different provider, set `LLM_MODEL` in `.env` (e.g., `LLM_MODEL=groq/llama-3.1-70b-versatile`).

## Architecture

### LangGraph Workflow Pipeline

The system uses LangGraph to orchestrate a Map-Reduce pattern with self-correction:

1. **Retrieve** → Query ChromaDB for reviews by Pueblo Mágico
2. **Map Phase** → Parallel insight extraction from review chunks
3. **Reduce Phase** → Synthesize insights into strategic briefing
4. **Audit Loop** → Self-correction verifying report against evidence (max 3 iterations)

Two workflow implementations exist:
- `voz_turista/application/workflow/graph.py` - Uses `ProjectState` with `Send()` for parallel chunk processing
- `voz_turista/application/workflow.py` - Simpler version with category-based parallelism (hotels, restaurants, attractions)

### Core Components

**Domain Layer** (`voz_turista/domain/`):
- `schemas.py` - Pydantic models: `Insight`, `InsightList`, `FullReport`, `AuditResult`
- `prompts/templates.py` - LLM prompt templates for extraction, synthesis, and auditing

**Infrastructure Layer** (`voz_turista/infrastructure/`):
- `llm_providers/` - Abstract `LLMProvider` base class with LiteLLM implementation (provider-agnostic)
- `database/chroma_client.py` - ChromaDB wrapper with HNSW cosine similarity, chunking support, and batch ingestion

**Application Layer** (`voz_turista/application/`):
- Workflow nodes: `retrieve_reviews_node`, `prepare_chunks_node`, `extract_insights_node`, `synthesize_report_node`, `auditor_node`
- State management via TypedDict with `operator.add` for accumulating insights

### Data Flow

Reviews are stored in ChromaDB with metadata: `town`, `polarity`, `type` (Hotel/Restaurant/Attractive), `place`, `month`, `year`. The `query_reviews` method requires a text query for semantic search combined with metadata filters.

### Structured Output

LLM responses use LiteLLM's `response_format` with Pydantic models to enforce structured output. Insights are classified by:
- `atribucion`: Pública (government) vs Privada (business)
- `dimension`: Recurso Natural, Servicio de Soporte, Gestión de Destino
- `urgencia`: Alta, Media, Baja
