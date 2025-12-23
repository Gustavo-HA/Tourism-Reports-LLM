# Documento de Diseño Técnico: Sistema de Inteligencia Turística

## 1. Arquitectura del Grafo (LangGraph)

El sistema utiliza una arquitectura basada en grafos cíclicos orquestada por **LangGraph**. El flujo principal sigue un patrón **Map-Reduce** con un bucle de **Auto-Corrección**.

### Componentes Clave:

*   **ProjectState**: Un `TypedDict` que mantiene el estado global, incluyendo las reviews crudas, los insights extraídos, el borrador del reporte y el historial de críticas.
*   **Nodos**:
    *   `prepare_chunks`: Divide la entrada masiva (300k reviews filtradas) en lotes manejables.
    *   `extract_insights` (Map): Procesa cada lote en paralelo para extraer información relevante sin perder contexto.
    *   `synthesize_report` (Reduce): Agrega los insights y genera la "Tarjeta de Presentación".
    *   `reviewer` (Crítico): Evalúa la calidad del reporte generado.

## 2. Lógica de Concurrencia y Escalabilidad

Para manejar el volumen de 300k registros, implementamos un patrón **Map-Reduce** utilizando la API `Send` de LangGraph.

### Estrategia de Procesamiento Paralelo:

1.  **Chunking Inteligente**: En lugar de pasar todas las reviews a un solo contexto de LLM (lo cual sería costoso y excedería los límites de tokens), el nodo `prepare_chunks` divide las reviews en subconjuntos (chunks) de tamaño `N` (ej. 50-100 reviews).
2.  **Mapeo Dinámico (`Send`)**: La función `map_reviews` genera dinámicamente una tarea `extract_insights` para cada chunk. LangGraph ejecuta estas tareas en paralelo (hasta el límite de concurrencia configurado).
3.  **Reducción Automática**: El estado `extracted_insights` está anotado con `operator.add`. Esto significa que cuando cada nodo paralelo termina, su salida se agrega automáticamente a la lista global de insights, sin necesidad de un nodo reductor complejo manual.

**Beneficios:**
*   **Latencia Reducida**: El tiempo de procesamiento se reduce drásticamente al paralelizar la lectura de reviews.
*   **Costos Optimizados**: Permite usar modelos más pequeños y rápidos para la fase de extracción (Map) y reservar modelos más potentes (ej. GPT-4o) solo para la síntesis final (Reduce).

## 3. Estrategia de Verificación y "Ground Truth"

Dado que no existen reportes humanos ideales para entrenamiento, la veracidad se garantiza mediante dos mecanismos:

### A. Self-Correction Loop (Implementado)
El nodo `reviewer` actúa como un juez imparcial.
1.  Recibe el `draft_report` y los `extracted_insights` originales.
2.  Evalúa si cada afirmación en el reporte tiene sustento en los insights (detección de alucinaciones).
3.  Si el `quality_score` es bajo (< 0.9), el grafo cicla de nuevo al nodo `synthesize_report`, pasando el feedback para que el modelo corrija los errores.

### B. Generación Sintética (Validación)
Para validar el sistema antes de producción:
1.  Se selecciona una muestra aleatoria de destinos.
2.  Un modelo "Teacher" (SOTA, ej. GPT-4o) genera reportes "Gold Standard" procesando las reviews con una ventana de contexto muy amplia (o ventana deslizante).
3.  Estos reportes sintéticos se usan como referencia para calcular métricas de similitud contra los reportes generados por nuestro sistema (más eficiente).

## 4. Métricas de Evaluación (Estilo RAGAS)

Para una tesis de ciencia de datos, se recomiendan las siguientes métricas:

### Métricas Cuantitativas (Evaluación Automática con LLM):

1.  **Faithfulness (Fidelidad):**
    *   *Definición:* ¿Qué porcentaje de las oraciones en el reporte final se pueden deducir lógicamente de los `extracted_insights`?
    *   *Objetivo:* Medir alucinaciones. Un score bajo indica que el modelo inventó información.

2.  **Answer Relevance (Relevancia):**
    *   *Definición:* ¿Qué tan bien responde el reporte a la estructura solicitada (Lo Bueno, Lo Malo, Tips)?
    *   *Objetivo:* Asegurar que el formato de "Tarjeta de Presentación" se respete.

3.  **Context Precision (Precisión del Contexto - Fase Map):**
    *   *Definición:* Evalúa si los insights extraídos en la fase Map son realmente representativos de las reviews originales.
    *   *Cálculo:* Comparación semántica entre los insights extraídos y un resumen de alto nivel del chunk de reviews.

### Métricas Cualitativas (Evaluación Humana):

*   **Utilidad del Tip:** Evaluar en una escala 1-5 si los "Consideraciones/Tips" son accionables para un turista (ej. "Lleva efectivo" vs "Es bonito").
*   **Coherencia Narrativa:** Fluidez y legibilidad del texto generado.
