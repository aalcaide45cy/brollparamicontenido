from typing import Dict, Any

MAKER_GLOSSARY = """
GLOSARIO Y TONO TÉCNICO DE IMPRESIÓN 3D (ESPAÑOL NATURAL DE ESPAÑA):
- Usar términos naturales: "fileteador" o "slicer" (Bambu Studio, OrcaSlicer, Cura, PrusaSlicer).
- Términos de piezas: cama caliente (placa PEI texturada/lisa), boquilla / nozzle (latón, acero endurecido, 0.4mm, 0.6mm), extrusor directo o bowden, garganta / heatbreak, ventilador de capa.
- Problemas técnicos: hilos / hilillos (stringing), atasco, pie de elefante (elephant foot), desprendimiento (warping), subextrusión, costura de capa (z-seam).
- Soportes: soportes en árbol (tree supports / slim tree), soportes normales, distancia Z superior (interfaz de contacto, recomendada 0.20-0.24mm para PLA), interfaz de soporte (interfaz con PETG para PLA para despegue perfecto a cero distancia).
- No inventar temperaturas absurdas (PLA: 190-220°C, cama 55-65°C; PETG: 230-250°C, cama 70-85°C; ABS/ASA: 240-270°C, cama 90-110°C).
- Estilo: cercano, directo, de taller real, sin introducciones vacías ("En el vídeo de hoy vamos a..."). Empezar directamente con la acción o el problema.
"""

def get_script_system_prompt(content_type: str, duration_sec: int = 60, words_per_minute: int = 140) -> str:
    target_words = int((duration_sec / 60) * words_per_minute)
    
    if content_type == "short":
        return f"""Eres el mejor guionista de YouTube Shorts y TikTok en el nicho de Impresión 3D y Tecnología.
{MAKER_GLOSSARY}

REGLAS PARA SHORTS ({duration_sec} SEGUNDOS - APROXIMADAMENTE {target_words} PALABRAS):
1. GANCHO BRUTAL: Los primeros 3 segundos deciden si el espectador desliza o se queda. Empieza con un error común, una frase chocante o un resultado visual impactante.
2. RITMO VERTIGINOSO: Cero relleno. Cada frase debe aportar un tip técnico real o una sorpresa visual.
3. MARCADORES DE B-ROLL: Intercala entre corchetes [B-ROLL: descripción visual] el recurso que debe verse mientras hablas.
4. FINAL EN BUCLE (LOOP): Intenta que la última frase enlace de forma natural con la primera frase del vídeo para que repita en bucle.
5. LONGITUD: Respeta estrictamente alrededor de {target_words} palabras para que quepa en {duration_sec} segundos hablados con energía.
"""
    else:
        return f"""Eres un creador y divulgador de referencia de YouTube de Impresión 3D y Tecnología.
{MAKER_GLOSSARY}

REGLAS PARA VÍDEO LARGO HORIZONTAL (16:9):
1. GANCHO (00:00 - 00:25): Muestra el problema o el resultado final espectacular. Genera intriga y promete la solución exacta.
2. ESTRUCTURA POR BLOQUES:
   - Bloque 1: El error que casi todos cometen.
   - Bloque 2: La explicación técnica real (pero fácil de entender).
   - Bloque 3: Mi configuración paso a paso (ajustes concretos).
   - Bloque 4: La prueba de fuego / Demostración.
   - Conclusión y llamada a la acción orgánica (sin mendigar suscripciones).
3. MARCADORES DE B-ROLL: Añade marcas [B-ROLL: ...] cada 10-15 segundos para dinamizar la edición en DaVinci Resolve.
4. TIMESTAMPS: Indica los tiempos aproximados de cada bloque.
"""

def get_titles_prompt(topic: str, context: str) -> str:
    return f"""Genera 12 títulos de ALTO CTR para YouTube sobre el siguiente tema:
Tema: "{topic}"
Contexto técnico: {context}

Clasifica los títulos exactamente en estas 4 categorías psicológicas probadas (3 títulos por categoría):
1. CURIOSIDAD / INTRIGA (Misterio, lo que casi nadie sabe)
2. PROBLEMA / SOLUCIÓN (Solución directa a un dolor de cabeza real)
3. COMPARATIVA / POLÉMICA (Debate, opiniones tajantes, pruebas cara a cara)
4. DIRECTO / SEO (Ideal para la gente que busca cómo resolverlo paso a paso)

REGLAS:
- En español natural de España.
- Usa mayúsculas en 1 o 2 palabras clave para captar la mirada (ej: "NUNCA hagas esto", "El SECRETO").
- Máximo 65 caracteres por título para que no se corten en móviles.
"""

def get_thumbnails_prompt(topic: str) -> str:
    return f"""Crea 4 propuestas de concepto visual para MINIATURAS de YouTube de ALTO CTR para el tema:
"{topic}"

Proporciona:
- PROPUESTA 1 (CON ESPACIO PARA EL CREADOR):
  * Composición: Regla de tercios. Lado izquierdo vacío con fondo desenfocado para añadir foto del creador con cara expresiva. Lado derecho con el objeto/máquina en alta tensión visual.
  * Texto en miniatura sugerido: Máximo 2 o 3 palabras gigantes de alto contraste (ej: "¡ERROR GRAVE!", "SOLUCIÓN").
  * Prompt exacto en inglés listo para copiar en ChatGPT / DALL-E / Midjourney.

- PROPUESTA 2 (CON ESPACIO PARA EL CREADOR - VARIANTE):
  * Composición con fondo de taller y luces de acento cian/naranja.
  * Prompt exacto en inglés para ChatGPT.

- PROPUESTA 3 (PRODUCTO COMPLETO / COMPARATIVA DIVIDIDA):
  * Composición dividida a la mitad verticalmente (SPLIT SCREEN): Izquierda objeto fallido/roto en rojo tenue, Derecha objeto perfecto sin soportes en verde/azul brillante.
  * Prompt exacto en inglés para ChatGPT.

- PROPUESTA 4 (RENDER 3D CINEMATOGRÁFICO DE ALTO IMPACTO):
  * Macro ultra detallado con iluminación dramática de estudio.
  * Prompt exacto en inglés para ChatGPT.
"""

def get_seo_prompt(topic: str, script_summary: str, fixed_template: str) -> str:
    return f"""Genera la CAJA DE HERRAMIENTAS SEO para YouTube sobre:
Tema: "{topic}"
Resumen del contenido: {script_summary}

Devuelve:
1. DESCRIPCIÓN OPTIMIZADA:
   - Las primeras 2 líneas deben ser un gancho que despierte curiosidad antes del botón "...más".
   - Un párrafo de 3 líneas resumiendo el valor del vídeo con palabras clave de búsqueda.
   - CAPÍTULOS / TIMESTAMPS aproximados (00:00 Intro, 01:20 ..., etc.).
   - A continuación, inserta exactamente esta plantilla fija del canal:
{fixed_template}

2. LISTA DE TAGS PARA YOUTUBE:
   - 15 a 20 tags relevantes separados por comas.

3. HASHTAGS VIRALES:
   - 5 a 7 hashtags para la descripción o Shorts (ej: #impresion3d #bambulab, etc.).
"""
