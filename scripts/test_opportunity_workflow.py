#!/usr/bin/env python
"""Test script for the Opportunity Workflow."""

import sys

from dotenv import load_dotenv

from voz_turista.application.opportunity_workflow import OpportunitySession

# Load env vars
load_dotenv()

def main():
    # Get pueblo magico from command line or use default
    pueblo_magico = sys.argv[1] if len(sys.argv) > 1 else "Isla_Mujeres"

    print(f"\n{'#'*60}")
    print(f"# Testing Opportunity Workflow for: {pueblo_magico}")
    print(f"{'#'*60}\n")

    # Create session
    session = OpportunitySession(pueblo_magico)

    # Phase 1: Generate Report
    print("\n[PHASE 1] Generating Opportunity Report...")
    print("-" * 40)

    report = session.generate_report()

    # Print summary
    print("\n" + session.get_report_summary())

    # Phase 2: Interactive Chat
    print("\n[PHASE 2] Testing Chat Mode...")
    print("-" * 40)

    test_queries = [
        "Cuales son las principales quejas sobre hoteles?",
        "Que problemas de servicio tienen los restaurantes?",
        "Dame ejemplos de resenas negativas sobre limpieza",
    ]

    for query in test_queries:
        print(f"\n>>> Usuario: {query}")
        response = session.chat(query)
        print(f"\n<<< Asistente: {response[:500]}...")
        print("-" * 40)

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
