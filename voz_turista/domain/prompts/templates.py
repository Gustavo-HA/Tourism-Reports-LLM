"""Prompt templates for the Opportunity Workflow."""

PROMPT_EXTRACT_OPPORTUNITIES = """
Analiza las siguientes resenas de {business_type}s en {pueblo_magico} y extrae hallazgos accionables para un briefing de inteligencia turistica dirigido a autoridades.

Busca patrones en:
1. Quejas recurrentes o problemas sistematicos
2. Servicios o amenidades ausentes que los turistas esperan
3. Comparaciones negativas con otros destinos
4. Sugerencias explicitas de los visitantes
5. Expectativas no cumplidas
6. Recursos naturales o culturales infrautilizados

Para cada hallazgo, proporciona:
- idx_review: IDs de las resenas que sustentan el hallazgo
- insight: Hallazgo conciso y accionable
- atribucion: Publica (infraestructura, senalizacion, seguridad, servicios basicos del gobierno) o Privada (gestion de negocios, calidad de servicio, capacitacion del personal)
- dimension: Una de [Recurso Natural, Servicio de Soporte, Gestion de Destino]
  - Recurso Natural: Playas, cenotes, areas naturales, patrimonio cultural, clima
  - Servicio de Soporte: Hospedaje, restaurantes, transporte, guias, comercio
  - Gestion de Destino: Planeacion, promocion, regulacion, limpieza urbana, seguridad
- urgencia: Alta (impacto directo en competitividad turistica), Media (molestia frecuente que afecta percepcion), Baja (mejora deseable pero no critica)
- actionable_suggestion: Una accion concreta para abordar el hallazgo

Reseñas a analizar:
{reviews}
"""

PROMPT_SYNTHESIZE_OPPORTUNITIES = """
Genera un reporte de inteligencia turistica en español para {business_type}s en {pueblo_magico} dirigido a autoridades.

Basandote en los insights recopilados, genera:
1. summary: Resumen ejecutivo (2-3 oraciones) de los principales hallazgos para este tipo de negocio
2. strengths: Lista de 3-5 fortalezas identificadas
3. gap_diagnosis: Lista de 3-5 brechas criticas — recursos infrautilizados por fallas publicas (gobierno/infraestructura) o privadas (gestion de negocios). Indica claramente si la brecha es de atribucion Publica o Privada.

Insights recopilados:
{insights}

Total de resenas analizadas: {total_reviews}
"""

PROMPT_CONSOLIDATE_REPORT = """
Genera un Briefing de Competitividad Estrategica para las autoridades turisticas de {pueblo_magico}, combinando los hallazgos de todos los tipos de negocio.

Estructura del briefing:

1. executive_summary: Vision general del destino — principales fortalezas, debilidades criticas y posicion competitiva (3-4 oraciones).

2. scorecard: Scorecard de Eficiencia Turistica. Califica del 1 al 10 cada pilar con una justificacion breve basada en la evidencia:
   - infraestructura: Transporte, senalizacion, accesos, servicios basicos
   - servicios: Hospedaje, restaurantes, guias, atencion al turista
   - atractivos: Recursos naturales, culturales, experiencias ofrecidas

3. gap_diagnosis: Diagnostico de Brechas (5-8 items). Identifica recursos infrautilizados por fallas macro (publicas: gobierno, infraestructura) o micro (privadas: gestion de negocios). Cada brecha debe ser especifica y accionable. Estas brechas deben ser subsecciones del briefing, no solo items en una lista:
    - Pública: 
      - brecha_1: Descripcion de la brecha, evidencia que la sustenta, y sugerencia de accion concreta para el gobierno
      - brecha_2: ...
    - Privada:
      - brecha_1: Descripcion de la brecha, evidencia que la sustenta, y sugerencia de accion concreta para el sector privado
      - brecha_2: ...

4. roadmap: Hoja de Ruta con acciones priorizadas:
   - inversion_publica: 3-5 acciones concretas que requieren inversion o gestion publica
   - capacitacion_privada: 3-5 acciones concretas para capacitacion o mejora del sector privado

5. cross_cutting_opportunities: Patrones transversales que afectan a multiples tipos de negocio (3-5 items).

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
