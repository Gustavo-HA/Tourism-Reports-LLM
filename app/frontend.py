"""Streamlit frontend for Voz Turista."""

import httpx
import streamlit as st

API_BASE = "http://localhost:8000"
REQUEST_TIMEOUT = 600.0

st.set_page_config(
    page_title="Voz Turista - Inteligencia Turistica",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------

_DEFAULTS: dict = {
    "session_id": None,
    "pueblo_magico": None,
    "report": None,
    "chat_history": [],
    "phase": "select",
}
for key, default in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_state():
    if st.session_state.session_id:
        try:
            httpx.delete(
                f"{API_BASE}/api/sessions/{st.session_state.session_id}",
                timeout=10.0,
            )
        except httpx.HTTPError:
            pass
    for key, default in _DEFAULTS.items():
        st.session_state[key] = default if not isinstance(default, list) else []


def render_report(report: dict, pueblo: str):
    st.header(f"Briefing de Competitividad Estrategica: {pueblo}")

    # Executive summary
    st.subheader("Resumen Ejecutivo")
    st.write(report.get("executive_summary", "No disponible"))

    # Scorecard
    st.subheader("Scorecard de Eficiencia Turistica")
    scorecard = report.get("scorecard", {})
    cols = st.columns(3)
    for col, pilar in zip(cols, ["infraestructura", "servicios", "atractivos"]):
        pilar_data = scorecard.get(pilar, {})
        if isinstance(pilar_data, dict):
            with col:
                st.metric(
                    label=pilar.capitalize(),
                    value=f"{pilar_data.get('score', 'N/A')}/10",
                )
                st.caption(pilar_data.get("justification", ""))

    # Gap diagnosis
    st.subheader("Diagnostico de Brechas")
    for gap in report.get("gap_diagnosis", []):
        st.markdown(f"- {gap}")

    # Roadmap
    st.subheader("Hoja de Ruta")
    roadmap = report.get("roadmap", {})
    col_pub, col_priv = st.columns(2)
    with col_pub:
        st.markdown("**Inversion Publica**")
        for i, action in enumerate(roadmap.get("inversion_publica") or [], 1):
            st.markdown(f"{i}. {action}")
    with col_priv:
        st.markdown("**Capacitacion Privada**")
        for i, action in enumerate(roadmap.get("capacitacion_privada") or [], 1):
            st.markdown(f"{i}. {action}")

    # Cross-cutting opportunities
    st.subheader("Oportunidades Transversales")
    for opp in report.get("cross_cutting_opportunities", []):
        st.markdown(f"- {opp}")

    # Per business type
    st.subheader("Detalle por Tipo de Negocio")
    for btype, breport in report.get("by_business_type", {}).items():
        with st.expander(
            f"{btype} ({breport.get('total_reviews_analyzed', 0)} reseñas)"
        ):
            st.write(breport.get("summary", "N/A"))
            if breport.get("strengths"):
                st.markdown("**Fortalezas:**")
                for s in breport["strengths"]:
                    st.markdown(f"- {s}")
            if breport.get("gap_diagnosis"):
                st.markdown("**Brechas:**")
                for g in breport["gap_diagnosis"]:
                    st.markdown(f"- {g}")


def render_chat():
    st.subheader("Chat Interactivo")
    st.caption("Haz preguntas sobre las reseñas y el reporte generado.")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Escribe tu pregunta..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Consultando..."):
                try:
                    resp = httpx.post(
                        f"{API_BASE}/api/sessions/{st.session_state.session_id}/chat",
                        json={"message": prompt},
                        timeout=120.0,
                    )
                    resp.raise_for_status()
                    answer = resp.json()["response"]
                except httpx.HTTPError as e:
                    answer = f"Error al consultar: {e}"
            st.markdown(answer)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": answer}
            )


# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------

st.title("Voz Turista")
st.subheader("Inteligencia Turistica para Pueblos Magicos de Mexico")

# ---- Phase: Select --------------------------------------------------------
if st.session_state.phase == "select":
    try:
        resp = httpx.get(f"{API_BASE}/api/pueblos", timeout=10.0)
        resp.raise_for_status()
        pueblos = resp.json()["pueblos"]
    except httpx.HTTPError:
        st.error(
            "No se pudo conectar con el servidor API. "
            "Asegurate de que el backend esta corriendo (`make api`)."
        )
        st.stop()

    pueblo_options = {p["display_name"]: p["name"] for p in pueblos}
    selected_display = st.selectbox(
        "Selecciona un Pueblo Magico:",
        options=list(pueblo_options.keys()),
        index=None,
        placeholder="Elige un pueblo...",
    )

    if selected_display and st.button("Generar Reporte", type="primary"):
        pueblo_name = pueblo_options[selected_display]
        try:
            resp = httpx.post(
                f"{API_BASE}/api/sessions",
                json={"pueblo_magico": pueblo_name},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            st.session_state.session_id = data["session_id"]
            st.session_state.pueblo_magico = pueblo_name
            st.session_state.phase = "report"
            st.rerun()
        except httpx.HTTPError as e:
            st.error(f"Error al crear la sesion: {e}")

# ---- Phase: Report generation ---------------------------------------------
elif st.session_state.phase == "report":
    pueblo_display = st.session_state.pueblo_magico.replace("_", " ")
    st.info(f"Generando reporte para **{pueblo_display}**...")

    with st.spinner(
        "Analizando reseñas y generando el briefing estrategico. "
        "Esto puede tardar varios minutos..."
    ):
        try:
            resp = httpx.post(
                f"{API_BASE}/api/sessions/{st.session_state.session_id}/generate",
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            st.session_state.report = data["report"]
            st.session_state.phase = "chat"
            st.rerun()
        except httpx.HTTPError as e:
            st.error(f"Error al generar el reporte: {e}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Volver a intentar"):
                    st.rerun()
            with col2:
                if st.button("Seleccionar otro pueblo"):
                    _reset_state()
                    st.rerun()

# ---- Phase: Chat (report display + interactive chat) ----------------------
elif st.session_state.phase == "chat":
    pueblo_display = st.session_state.pueblo_magico.replace("_", " ")

    with st.sidebar:
        st.header(pueblo_display)
        if st.button("Nuevo analisis"):
            _reset_state()
            st.rerun()
        if st.button("Limpiar chat"):
            try:
                httpx.post(
                    f"{API_BASE}/api/sessions/{st.session_state.session_id}/clear-chat",
                    timeout=10.0,
                )
            except httpx.HTTPError:
                pass
            st.session_state.chat_history = []
            st.rerun()

    tab_report, tab_chat = st.tabs(["Reporte", "Chat"])

    with tab_report:
        render_report(st.session_state.report, pueblo_display)

    with tab_chat:
        render_chat()
