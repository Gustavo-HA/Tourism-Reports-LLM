# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tourism intelligence report generation system for México's Pueblos Mágicos using LLMs and RAG. Analyzes TripAdvisor reviews to produce strategic briefings ("Briefing de Competitividad Estratégica") for tourism authorities.

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

# Run opportunity workflow (primary workflow)
python scripts/test_opportunity_workflow.py [pueblo_magico]
# e.g.: python scripts/test_opportunity_workflow.py Isla_Mujeres

# Run legacy workflow
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

Requires a `.env` file with API keys and model configuration. LiteLLM reads keys from standard env vars:
- `GEMINI_API_KEY` - Google Gemini
- `OPENAI_API_KEY` - OpenAI
- `ANTHROPIC_API_KEY` - Anthropic
- `GROQ_API_KEY` - Groq

Required settings in `.env` (no defaults in code):
- `LLM_MODEL` — LiteLLM model identifier (e.g., `gemini/gemini-2.5-flash`, `groq/llama-3.1-70b-versatile`)
- `EMBEDDING_MODEL` — sentence-transformers model (e.g., `hiiamsid/sentence_similarity_spanish_es`)
- `LLM_TEMPERATURE` — optional, defaults to `0.0`
- `VECTOR_DB_PATH` — path to vector database (e.g., `data/chromadb/restmex_sss_cs200_ov50/`)
- `VECTOR_DB_COLLECTION` - vector database collection name (e.g., `restmex_sss_cs200_ov50`)
- `RERANKER_MODEL` — optional cross-encoder model for two-stage retrieval reranking (e.g., `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`). Disabled when unset.

## Architecture

### Opportunity Workflow (Primary)

Located in `voz_turista/application/opportunity_workflow/`. Uses LangGraph with a Map-Reduce pattern, self-correction audit loop, and interactive chat. Orchestrated via `OpportunitySession`.

**Report Generation Graph** (`graph.py: build_report_workflow`):
1. **Retrieve** → Query ChromaDB for reviews by Pueblo Mágico, split by business type (Hotel, Restaurant, Attractive)
2. **Map Phase** → Parallel insight extraction from review chunks via `Send()` (chunk_size=15)
3. **Reduce Phase** → Synthesize insights per business type, then consolidate into a unified briefing
4. **Audit Loop** → Self-correction verifying report against original review evidence (max 3 iterations)

**Chat Graph** (`graph.py: build_chat_workflow`):
1. **Parse Query** → Extract ChromaDB filters and semantic search query from user message
2. **Execute Query** → Run the search against ChromaDB
3. **Generate Response** → Produce a contextual answer using report context + query results + chat history

**Session** (`session.py: OpportunitySession`):
- `generate_report()` → runs the report graph, stores the consolidated report
- `chat(query)` → runs the chat graph with report context, maintains message history

### Legacy Workflow

Two older implementations exist for reference:
- `voz_turista/application/workflow/` — uses `ProjectState` with `Send()` for parallel chunk processing
- `voz_turista/application/workflow.py` — simpler version with category-based parallelism

### Core Components

**Domain Layer** (`voz_turista/domain/`):
- `schemas.py` — Pydantic models for both workflows:
  - Base workflow: `Insight`, `InsightList`, `FullReport`, `AuditResult`
  - Opportunity workflow: `Review`, `ExtractedOpportunityInsight`, `BusinessTypeSynthesis`, `ConsolidatedReport`, `Scorecard`, `PillarScore`, `RoadmapActions`, `ParsedQuery`
- `prompts/templates.py` — LLM prompt templates for legacy workflow

**Infrastructure Layer** (`voz_turista/infrastructure/`):
- `llm_providers/` — Abstract `LLMProvider` base class with `LiteLLMProvider` (provider-agnostic via LiteLLM) and legacy `GoogleProvider`
- `database/chroma_client.py` — ChromaDB wrapper with HNSW cosine similarity, chunking support, and batch ingestion

**Application Layer** (`voz_turista/application/`):
- `opportunity_workflow/` — primary workflow with nodes, prompts, state, graph, and session management
- `workflow/` and `workflow.py` — legacy implementations
- State management via TypedDict with `operator.add` for accumulating insights across parallel map tasks

### Tourism Intelligence Taxonomy

Insights are classified using a taxonomy oriented toward tourism authorities:
- **Atribución**: Pública (government infrastructure, signage, public safety, basic services) vs Privada (business management, service quality, staff training)
- **Dimensión**: Recurso Natural, Servicio de Soporte, Gestión de Destino
- **Urgencia**: Alta (direct competitiveness impact), Media (frequent perception issue), Baja (desirable improvement)

**Consolidated Report Structure** (`ConsolidatedReport`):
1. **Executive Summary** — destination overview and competitive position
2. **Scorecard de Eficiencia Turística** — 1-10 scores for infraestructura, servicios, atractivos (each with justification)
3. **Diagnóstico de Brechas** — underutilized resources from public or private failures
4. **Hoja de Ruta** — prioritized actions split into inversión pública vs capacitación privada
5. **Oportunidades Transversales** — cross-cutting patterns across business types

### Data Flow

Reviews are stored in ChromaDB with metadata: `town`, `polarity`, `type` (Hotel/Restaurant/Attractive), `place`, `month`, `year`. The `query_reviews` method requires a text query for semantic search combined with metadata filters.

### Structured Output

LLM responses use LiteLLM's `response_format` with Pydantic models to enforce structured output. The `LiteLLMProvider.generate_structured()` method accepts a Pydantic schema class and returns a validated instance.
