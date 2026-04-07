"""FastAPI backend for Voz Turista."""

import csv
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import mlflow
import mlflow.langchain
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from voz_turista.application.workflow import OpportunitySession
from voz_turista.config import settings
from voz_turista.infrastructure.llm_providers.litellm_provider import LiteLLMProvider

logger = logging.getLogger(__name__)

PUEBLOS_CSV = Path("data/PueblosMagicos/interim/unique_pueblos.csv")

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class PuebloItem(BaseModel):
    name: str
    display_name: str


class PuebloListResponse(BaseModel):
    pueblos: list[PuebloItem]


class CreateSessionRequest(BaseModel):
    pueblo_magico: str


class SessionResponse(BaseModel):
    session_id: str
    pueblo_magico: str
    status: str


class GenerateReportResponse(BaseModel):
    session_id: str
    status: str
    report: dict[str, Any] | None = None
    report_summary: str | None = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    history_length: int


class StatusResponse(BaseModel):
    session_id: str
    pueblo_magico: str
    status: str
    has_report: bool
    chat_history_length: int
    error_message: str | None = None


# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------

pueblos_catalog: list[PuebloItem] = []
sessions: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    with open(PUEBLOS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Pueblo"].strip()
            if name:
                pueblos_catalog.append(
                    PuebloItem(
                        name=name,
                        display_name=name.replace("_", " "),
                    )
                )
    pueblos_catalog.sort(key=lambda p: p.display_name)
    logger.info("Cargados %d pueblos del catálogo.", len(pueblos_catalog))
    mlflow.set_experiment("Voz Turista - API")
    mlflow.langchain.autolog()
    logger.info("MLflow tracing activo: %s", mlflow.get_tracking_uri())
    yield


app = FastAPI(title="Voz Turista API", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/pueblos", response_model=PuebloListResponse)
def list_pueblos():
    return PuebloListResponse(pueblos=pueblos_catalog)


@app.post("/api/sessions", response_model=SessionResponse, status_code=201)
def create_session(req: CreateSessionRequest):
    valid_names = {p.name for p in pueblos_catalog}
    if req.pueblo_magico not in valid_names:
        raise HTTPException(
            status_code=404,
            detail=f"Pueblo '{req.pueblo_magico}' no encontrado en el catálogo.",
        )

    provider = LiteLLMProvider(
        model_name=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
    )
    session = OpportunitySession(req.pueblo_magico, llm_provider=provider)
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "session": session,
        "pueblo_magico": req.pueblo_magico,
        "status": "created",
        "error_message": None,
        "created_at": datetime.now(),
    }
    logger.info("Sesión creada: %s → %s", session_id, req.pueblo_magico)
    return SessionResponse(
        session_id=session_id,
        pueblo_magico=req.pueblo_magico,
        status="created",
    )


@app.post(
    "/api/sessions/{session_id}/generate",
    response_model=GenerateReportResponse,
)
def generate_report(session_id: str):
    entry = sessions.get(session_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")

    if entry["status"] == "ready":
        s = entry["session"]
        return GenerateReportResponse(
            session_id=session_id,
            status="ready",
            report=s.report,
            report_summary=s.get_report_summary(),
        )

    entry["status"] = "generating"
    pueblo = entry["pueblo_magico"]
    logger.info("Iniciando generación: %s (%s)", session_id, pueblo)
    t0 = time.perf_counter()
    try:
        with mlflow.start_span(name="generate_report", span_type="chain") as span:
            span.set_inputs({"session_id": session_id, "pueblo_magico": pueblo})
            report = entry["session"].generate_report()
            elapsed = time.perf_counter() - t0
            span.set_outputs({"status": "ready", "elapsed_seconds": round(elapsed, 1)})
        entry["status"] = "ready"
        logger.info("Reporte generado: %s en %.1fs", session_id, elapsed)
        return GenerateReportResponse(
            session_id=session_id,
            status="ready", 
            report=report,
            report_summary=entry["session"].get_report_summary(),
        )
    except Exception as e:
        entry["status"] = "error"
        entry["error_message"] = str(e)
        logger.exception("Error generando reporte para sesión %s", session_id)
        raise HTTPException(
            status_code=500, detail=f"Error generando reporte: {e}"
        ) from e


@app.get("/api/sessions/{session_id}", response_model=StatusResponse)
def get_session_status(session_id: str):
    entry = sessions.get(session_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    s = entry["session"]
    return StatusResponse(
        session_id=session_id,
        pueblo_magico=entry["pueblo_magico"],
        status=entry["status"],
        has_report=s.report is not None,
        chat_history_length=len(s.messages),
        error_message=entry["error_message"],
    )


@app.post("/api/sessions/{session_id}/chat", response_model=ChatResponse)
def chat(session_id: str, req: ChatRequest):
    entry = sessions.get(session_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    if entry["status"] != "ready":
        raise HTTPException(
            status_code=400, detail="El reporte aún no ha sido generado."
        )

    logger.info("Chat: %s | query=%r", session_id, req.message[:60])
    with mlflow.start_span(name="chat", span_type="chain") as span:
        span.set_inputs({"session_id": session_id, "pueblo_magico": entry["pueblo_magico"], "message": req.message})
        response = entry["session"].chat(req.message)
        span.set_outputs({"response_length": len(response)})
    return ChatResponse(
        response=response,
        history_length=len(entry["session"].messages),
    )


@app.post("/api/sessions/{session_id}/clear-chat", status_code=204)
def clear_chat(session_id: str):
    entry = sessions.get(session_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    entry["session"].clear_chat_history()


@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    del sessions[session_id]
