# Templates para prompts
SYSTEM_PROMPT_EXTRACT = """
Analiza las siguientes reseñas sobre {pueblo_magico} y extrae insights clave.
Formato JSON esperado:
[
  {{"insight": "...", "sentiment": "...", "category": "..."}}
]
"""

SYSTEM_PROMPT_SYNTHESIZE = """
Actúa como un experto en turismo. Genera una tarjeta de presentación para {pueblo_magico} basada en los siguientes insights.
Incluye: Scorecard, Lo Bueno, Áreas de Oportunidad y Consideraciones.
"""
