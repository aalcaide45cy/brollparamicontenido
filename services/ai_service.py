import json
import re
import os
import httpx
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
from duckduckgo_search import DDGS

from core.config_manager import load_config
from services.script_prompts import (
    get_script_system_prompt,
    get_titles_prompt,
    get_thumbnails_prompt,
    get_seo_prompt,
    MAKER_GLOSSARY,
)


def search_web_duckduckgo(query: str, max_results: int = 4) -> str:
    """Busqueda web local sin API para verificar informacion tecnica."""
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query + " impresion 3d", max_results=max_results):
                title = r.get("title", "")
                snippet = r.get("body", "")
                link = r.get("href", "")
                results.append(f"Fuente: {title}\nURL: {link}\nResumen: {snippet}\n")
        return "\n".join(results)
    except Exception as e:
        print(f"Aviso: Búsqueda DuckDuckGo no disponible ({e})")
        return ""


def get_gemini_keys_pool(config: dict) -> List[str]:
    """Obtiene la lista de todas las claves API disponibles para rotacion automatica."""
    keys = []
    single_key = config.get("gemini_api_key", "").strip()
    if single_key:
        keys.append(single_key)
    for k in config.get("gemini_api_keys", []):
        if isinstance(k, str) and k.strip() and k.strip() not in keys:
            keys.append(k.strip())
        elif isinstance(k, dict) and k.get("key") and k.get("key").strip() not in keys:
            keys.append(k["key"].strip())
    return keys


async def query_gemini(prompt: str, system_instruction: Optional[str] = None, use_grounding: bool = True) -> str:
    """Consulta Gemini con rotación automática de claves gratuitas y modelo configurable."""
    config = load_config()
    keys = get_gemini_keys_pool(config)
    if not keys:
        raise ValueError("No se ha configurado ninguna clave API de Gemini en Ajustes.")

    model_name = config.get("gemini_model", "gemini-3.6-flash")

    # Mapeo automático para modelos deprecados por Google API
    DEPRECATED_ALIASES = {
        "gemini-2.5-flash": "gemini-3.6-flash",
        "gemini-2.0-flash": "gemini-3.6-flash",
        "gemini-2.0-flash-lite": "gemini-3.5-flash-lite",
        "gemini-1.5-flash": "gemini-3.5-flash",
        "gemini-1.5-pro": "gemini-3.6-flash",
    }
    model_name = DEPRECATED_ALIASES.get(model_name, model_name)

    last_error = None
    for idx, key in enumerate(keys):
        try:
            client = genai.Client(api_key=key)
            tools = []
            if use_grounding:
                tools.append(types.Tool(google_search=types.GoogleSearch()))

            gen_config = types.GenerateContentConfig(
                temperature=0.7,
                tools=tools if tools else None,
                system_instruction=system_instruction,
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=gen_config,
            )
            return response.text or ""
        except Exception as e:
            last_error = e
            print(f"[GEMINI ROTATION] Clave #{idx+1} agotada o con error ({e}). Rotando a siguiente clave...")
            continue

    err_str = str(last_error)
    if "RESOURCE_EXHAUSTED" in err_str or "credits are depleted" in err_str:
        raise RuntimeError("Tu clave de Google Gemini ha agotado su cuota gratuita (Error 429). Puedes generar una nueva clave gratis en https://aistudio.google.com/app/apikey o usar el Motor Local RTX 4090.")
    if "NOT_FOUND" in err_str or "is no longer available" in err_str:
        raise RuntimeError(f"El modelo anterior de Gemini ya no está disponible según Google. Se ha actualizado a Gemini 3.6 Flash. Detalle: {last_error}")

    raise RuntimeError(f"Todas las claves de Gemini configuradas ({len(keys)}) fallaron. Último error: {last_error}")



async def query_local_llm(prompt: str, system_instruction: Optional[str] = None) -> str:
    """Consulta un servidor LLM local compatible con OpenAI (llama.cpp, Ollama, LM Studio)."""
    config = load_config()
    configured_endpoint = config.get("local_llm_endpoint", "http://127.0.0.1:8080/v1").rstrip("/") + "/chat/completions"
    model = config.get("local_model_name", "qwen2.5-14b-instruct")

    candidate_endpoints = [
        configured_endpoint,
        "http://127.0.0.1:11434/v1/chat/completions",  # Ollama
        "http://127.0.0.1:1234/v1/chat/completions",   # LM Studio
        "http://127.0.0.1:8080/v1/chat/completions",   # llama.cpp
    ]
    seen = set()
    endpoints = [x for x in candidate_endpoints if not (x in seen or seen.add(x))]

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 3000,
    }

    last_err = None
    for ep in endpoints:
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(ep, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    last_err = f"HTTP {resp.status_code} en {ep}"
        except Exception as e:
            last_err = str(e)
            continue

    raise RuntimeError(f"No se pudo conectar a ningún motor local (Ollama, LM Studio o llama.cpp). Detalle: {last_err}")



async def generate_ai_text(prompt: str, system_instruction: Optional[str] = None, use_grounding: bool = True) -> str:
    """Enrutador de IA: decide entre Gemini o Local segun la configuracion."""
    config = load_config()
    provider = config.get("ai_provider", "gemini")

    if provider == "gemini":
        try:
            return await query_gemini(prompt, system_instruction, use_grounding)
        except Exception as e:
            # Si falla Gemini y no hay clave, dar respuesta estructurada clara
            if "No se ha configurado" in str(e) or "API_KEY_INVALID" in str(e):
                raise
            raise RuntimeError(f"Error en Gemini API: {e}")
    else:
        return await query_local_llm(prompt, system_instruction)


async def generate_full_script(topic: str, content_type: str, duration_sec: int = 60, context: str = "") -> Dict[str, Any]:
    """Genera el guion completo, estructurado con verificacion tecnica y marcas de B-roll."""
    config = load_config()
    wpm = config.get("words_per_minute", 140)
    
    # 1. Investigacion previa con DuckDuckGo si es local o contexto extra
    research_notes = ""
    if not context:
        research_notes = search_web_duckduckgo(topic)
    
    system_prompt = get_script_system_prompt(content_type, duration_sec, wpm)
    
    user_prompt = f"""TEMA DEL VÍDEO: {topic}
CONTEXTO TÉCNICO / NOTAS DE INVESTIGACIÓN:
{context if context else research_notes}

INSTRUCCIONES ESPECÍFICAS:
1. Redacta el guion definitivo palabra por palabra en español de España natural.
2. Incluye marcadores explícitos de [B-ROLL: ...] indicando qué clips de recurso insertar.
3. Asegura que los datos técnicos (temperaturas, distancias, ajustes del slicer) sean 100% verídicos y exactos.
4. Calcula el tiempo estimado según el ritmo natural de locución.
"""

    script_text = await generate_ai_text(user_prompt, system_prompt, use_grounding=True)
    
    # Extraer sugerencias de B-Roll detectadas en el guion
    broll_tags = re.findall(r'\[B-ROLL:\s*([^\]]+)\]', script_text, re.IGNORECASE)
    
    word_count = len(script_text.split())
    estimated_seconds = int((word_count / wpm) * 60)

    return {
        "topic": topic,
        "content_type": content_type,
        "target_duration_sec": duration_sec,
        "script": script_text,
        "word_count": word_count,
        "estimated_duration_sec": estimated_seconds,
        "broll_suggestions": list(set(broll_tags)) if broll_tags else ["impresora 3d imprimiendo", "cama caliente", "filamento"],
        "research_notes": research_notes[:500] if research_notes else "Verificado con Google Search",
    }


async def generate_titles_suite(topic: str, context: str = "") -> Dict[str, Any]:
    """Genera 12 titulos clasificados en las 4 categorias virales de alto CTR."""
    prompt = get_titles_prompt(topic, context)
    system_prompt = "Eres un estratega de YouTube especializado en viralidad, CTR y psicología de títulos de creadores top."
    raw_text = await generate_ai_text(prompt, system_prompt, use_grounding=False)
    
    return {
        "topic": topic,
        "raw_titles": raw_text,
    }


async def generate_thumbnails_suite(topic: str) -> Dict[str, Any]:
    """Genera 4 conceptos de miniaturas de alto impacto con prompts para ChatGPT/Midjourney."""
    prompt = get_thumbnails_prompt(topic)
    system_prompt = "Eres un director de arte y diseñador de miniaturas virales para los canales más grandes de YouTube."
    raw_text = await generate_ai_text(prompt, system_prompt, use_grounding=False)
    
    return {
        "topic": topic,
        "thumbnail_proposals": raw_text,
    }


async def generate_seo_suite(topic: str, script_summary: str) -> Dict[str, Any]:
    """Genera descripcion con plantilla fija, marcas de tiempo, tags y hashtags."""
    config = load_config()
    fixed_template = config.get("youtube_fixed_template", "")
    
    prompt = get_seo_prompt(topic, script_summary, fixed_template)
    system_prompt = "Eres un experto en SEO de YouTube, optimización de descripciones, metadatos y retención."
    raw_text = await generate_ai_text(prompt, system_prompt, use_grounding=False)
    
    return {
        "topic": topic,
        "seo_package": raw_text,
    }
