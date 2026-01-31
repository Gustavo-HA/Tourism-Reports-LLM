"""Prompt templates for the Opportunity Workflow."""

PROMPT_EXTRACT_OPPORTUNITIES = """
Analiza las siguientes resenas de {business_type}s en {pueblo_magico} e identifica AREAS DE OPORTUNIDAD.

Busca patrones en:
1. Quejas recurrentes o problemas sistematicos
2. Servicios o amenidades ausentes que los turistas esperan
3. Comparaciones negativas con otros destinos
4. Sugerencias explicitas de los visitantes
5. Expectativas no cumplidas

Para cada oportunidad identificada, proporciona:
- idx_review: IDs de las resenas que sustentan el hallazgo
- insight: Descripcion concisa del area de mejora
- category: Una de [Infraestructura, Servicio, Experiencia, Precio, Ubicacion, Limpieza]
- priority: Alta (afecta satisfaccion general), Media (molestia frecuente), Baja (mejora nice-to-have)
- actionable_suggestion: Una accion concreta para abordar la oportunidad

Resenas a analizar:
{reviews}
"""

PROMPT_SYNTHESIZE_OPPORTUNITIES = """
Genera un reporte de oportunidades para {business_type}s en {pueblo_magico} basado en los insights recopilados.

Estructura del reporte:
1. summary: Resumen ejecutivo (2-3 oraciones) de las principales oportunidades
2. opportunity_areas: Lista de las oportunidades mas importantes (ya proporcionadas)
3. strengths: Lista de 3-5 fortalezas identificadas en las resenas
4. total_reviews_analyzed: Numero total de resenas analizadas

Insights recopilados:
{insights}

Total de resenas analizadas: {total_reviews}
"""

PROMPT_CONSOLIDATE_REPORT = """
Genera un reporte consolidado de oportunidades para {pueblo_magico} combinando los hallazgos de todos los tipos de negocio.

Estructura del reporte final:
1. executive_summary: Vision general de las principales oportunidades del destino (3-4 oraciones)
2. by_business_type: Resumen de oportunidades por tipo (Hotel, Restaurant, Attractive)
3. cross_cutting_opportunities: Patrones que afectan a multiples tipos de negocio
4. priority_matrix: Clasificacion de acciones por urgencia e impacto
5. recommended_actions: Top 5 acciones concretas priorizadas

Reportes por tipo de negocio:
{business_reports}
"""

PROMPT_AUDIT_REPORT = """
Actua como un Auditor de Datos. Tu tarea es verificar que el siguiente reporte de oportunidades
para {pueblo_magico} este respaldado por la evidencia original.

Reporte:
{report}

Evidencia (Muestra de resenas):
{evidence}

Tarea:
1. Verifica que cada oportunidad identificada tenga sustento en las resenas
2. Identifica cualquier afirmacion que no este sustentada por la evidencia
3. Si el reporte es preciso, aprueba con "APROBADO"
4. Si hay errores significativos, marca como "RECHAZADO" y lista las correcciones necesarias
"""

PROMPT_PARSE_QUERY = """
Extrae filtros de busqueda de la siguiente consulta del usuario para buscar resenas en {pueblo_magico}.

Metadatos disponibles para filtrar:
- type: Tipo de negocio [Hotel, Restaurant, Attractive]
- polarity: Calificacion numerica (1-5, donde 1 es muy negativo y 5 es muy positivo)
- place: Nombre del establecimiento especifico
- month: Mes (1-12)
- year: Ano (ej. 2023, 2024)

Consulta del usuario: "{user_query}"

Responde con:
1. text_query: La consulta semantica para buscar (reescrita si es necesario para mejor recuperacion)
2. filters: Diccionario con los filtros detectados (solo incluir los mencionados explicitamente)
3. requires_report_context: Boolean indicando si la consulta hace referencia al reporte generado

Ejemplos:
- "Muestrame quejas sobre hoteles del 2024" ->
  text_query: "quejas problemas insatisfaccion", filters: {{"type": "Hotel", "year": 2024}}, requires_report_context: false
- "Dame mas detalles sobre el problema de limpieza que mencionaste" ->
  text_query: "limpieza suciedad higiene", filters: {{}}, requires_report_context: true
- "Que dicen de los restaurantes con mala calificacion?" ->
  text_query: "mala experiencia problemas", filters: {{"type": "Restaurant", "polarity": [1, 2]}}, requires_report_context: false
"""

PROMPT_CHAT_RESPONSE = """
Eres un asistente experto en turismo para {pueblo_magico}. Ayudas a analizar resenas de visitantes.

Contexto del reporte generado:
{report_summary}

Resultados de la busqueda actual ({num_results} resenas encontradas):
{query_results}

Historial de conversacion:
{chat_history}

Consulta actual del usuario: {user_query}

Instrucciones:
1. Responde de manera informativa y concisa
2. Si hay resultados relevantes, cita ejemplos especificos de las resenas
3. Si la consulta hace referencia al reporte, conecta la informacion con los hallazgos previos
4. Si no hay resultados, sugiere consultas alternativas
5. Responde en espanol
"""
