"""Render and save the report-generation and chat LangGraph workflow diagrams."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from voz_turista.application.workflow.graph import build_chat_workflow, build_report_workflow

OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "graphs"


def save_graph(graph, name: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Mermaid source
    mermaid_path = OUTPUT_DIR / f"{name}.md"
    mermaid_src = graph.get_graph().draw_mermaid()
    mermaid_path.write_text(f"```mermaid\n{mermaid_src}\n```\n")
    print(f"Mermaid saved: {mermaid_path}")

    # PNG (requires pygraphviz or pillow + mermaid-py)
    try:
        png_path = OUTPUT_DIR / f"{name}.png"
        png_bytes = graph.get_graph().draw_mermaid_png()
        png_path.write_bytes(png_bytes)
        print(f"PNG saved:     {png_path}")
    except Exception as exc:
        print(f"PNG skipped ({exc}). Install 'pygraphviz' or use the Mermaid file.", file=sys.stderr)


def main() -> None:
    print("Building report workflow…")
    report_graph = build_report_workflow()
    save_graph(report_graph, "report_workflow")

    print("\nBuilding chat workflow…")
    chat_graph = build_chat_workflow()
    save_graph(chat_graph, "chat_workflow")


if __name__ == "__main__":
    main()
