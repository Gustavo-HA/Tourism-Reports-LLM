# Templates para prompts

SYSTEM_PROMPT_EXTRACT = """
Analiza las reseñas de {pueblo_magico} y extrae un JSON con una lista de objetos que contengan:

- idx_review: IDs de referencia de las reseñas que sustentan el hallazgo.
- insight: Hallazgo conciso y accionable.
- atribucion: [Pública (Infraestructura) | Privada (Gestión)]. Clasifica si el problema/oportunidad recae en el gobierno o en los negocios privados.
- dimension: [Recurso Natural | Servicio de Soporte | Gestión de Destino].
- urgencia: [Alta | Media | Baja] según el impacto en la competitividad turística.

Reseñas:
{reviews}
"""

SYSTEM_PROMPT_SYNTHESIZE = """
Genera un Briefing de Competitividad Estratégica para las autoridades de {pueblo_magico} basado en los insights proporcionados.

Estructura del reporte (en formato JSON):
1. Scorecard de Eficiencia: Calificación del 1 al 10 por pilares (Infraestructura, Servicios, Atractivos).
2. Diagnóstico de Brechas (Gaps): Identifica recursos infrautilizados por fallas macro (públicas) o micro (privadas).
3. Hoja de Ruta: Priorización de inversión pública vs. capacitación privada. Sugiere 3 acciones concretas para cada una.

Insights:
{insights}
"""

SYSTEM_PROMPT_AUDITOR = """
Actúa como un Auditor de Datos. Tu tarea es verificar que el siguiente reporte generado para {pueblo_magico} esté respaldado por la evidencia original.

Reporte:
{report}

Evidencia (Muestra de reseñas):
{evidence}

Tarea:
1. Identifica cualquier afirmación en el reporte que no esté sustentada por la evidencia o que sea una alucinación.
2. Si el reporte es preciso, aprueba con "APROBADO".
3. Si hay errores, genera un JSON con las correcciones necesarias y marca como "RECHAZADO".
"""
