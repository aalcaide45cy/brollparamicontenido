import re
import os
import asyncio
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.config_manager import load_config

PEXELS_VIDEOS_URL = "https://api.pexels.com/videos/search"
PIXABAY_VIDEOS_URL = "https://pixabay.com/api/videos/"


def clean_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    return cleaned.strip().replace(" ", "_")[:60]


async def search_broll_pexels(query: str, api_key: str, per_page: int = 15, client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
    if not api_key:
        return []
    
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "landscape",
        "size": "large"
    }
    
    results = []
    try:
        if client:
            resp = await client.get(PEXELS_VIDEOS_URL, headers=headers, params=params)
        else:
            async with httpx.AsyncClient(timeout=10.0) as c:
                resp = await c.get(PEXELS_VIDEOS_URL, headers=headers, params=params)

        if resp.status_code == 200:
            data = resp.json()
            for v in data.get("videos", []):
                video_files = v.get("video_files", [])
                if not video_files:
                    continue
                
                video_files.sort(key=lambda x: x.get("width", 0), reverse=True)
                best_file = video_files[0]
                preview_file = next((f for f in reversed(video_files) if f.get("width", 0) >= 480), best_file)

                results.append({
                    "id": f"pexels_{v.get('id')}",
                    "source": "Pexels",
                    "title": f"Clip {v.get('id')} - {query}",
                    "thumbnail": v.get("image", ""),
                    "preview_url": preview_file.get("link", ""),
                    "download_url": best_file.get("link", ""),
                    "duration": v.get("duration", 0),
                    "width": best_file.get("width", 1920),
                    "height": best_file.get("height", 1080),
                    "quality": f"{best_file.get('width')}x{best_file.get('height')}",
                })
    except Exception as e:
        print(f"Error buscando en Pexels ({query}): {e}")
    return results


async def search_broll_pixabay(query: str, api_key: str, per_page: int = 20, client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
    if not api_key:
        return []
    
    params = {
        "key": api_key,
        "q": query,
        "per_page": per_page,
        "video_type": "all"
    }
    
    results = []
    try:
        if client:
            resp = await client.get(PIXABAY_VIDEOS_URL, params=params)
        else:
            async with httpx.AsyncClient(timeout=10.0) as c:
                resp = await c.get(PIXABAY_VIDEOS_URL, params=params)

        if resp.status_code == 200:
            data = resp.json()
            for hit in data.get("hits", []):
                videos = hit.get("videos", {})
                best = videos.get("large") or videos.get("medium") or videos.get("small")
                preview = videos.get("tiny") or videos.get("small") or best
                
                if not best:
                    continue

                thumb_url = (
                    videos.get("medium", {}).get("thumbnail")
                    or videos.get("large", {}).get("thumbnail")
                    or videos.get("small", {}).get("thumbnail")
                    or videos.get("tiny", {}).get("thumbnail")
                    or hit.get("userImageURL", "")
                )

                results.append({
                    "id": f"pixabay_{hit.get('id')}",
                    "source": "Pixabay",
                    "title": hit.get("tags", f"Clip {hit.get('id')}"),
                    "thumbnail": thumb_url,
                    "preview_url": preview.get("url", ""),
                    "download_url": best.get("url", ""),
                    "duration": hit.get("duration", 0),
                    "width": best.get("width", 1920),
                    "height": best.get("height", 1080),
                    "quality": f"{best.get('width')}x{best.get('height')}",
                })
    except Exception as e:
        print(f"Error buscando en Pixabay ({query}): {e}")
    return results


# Palabras de descarte absoluto (ruido de bancos de stock que no tienen nada que ver con impresión 3D)
JUNK_STOCK_TAGS = {
    "earth", "planet", "wormhole", "space", "galaxy", "universe", "stars",
    "bitcoin", "crypto", "blockchain", "money", "currency", "finance", "pay", "payment",
    "beach", "sand", "sea", "ocean", "mediterranean", "dune", "mountain", "mountains", 
    "clouds", "sky", "sunset", "sunrise",
    "church", "cathedral", "monument", "castle", "tourism", "cityscape", "ferris wheel",
    "biology", "genetics", "dna", "virus", "medical", "cell", "bacteria", "ribonucleic",
    "letters", "alphabet", "typography", "count", "shopping",
    "light bulb", "bulb", "lamp", "candle", "incandescent",
    "bird", "birds", "butterfly", "insect", "wildlife", "lake",
    "abstract", "wallpaper", "particles", "atom", "molecule"
}

# Diccionario semántico contextual especializado para canal de YouTube de Impresión 3D y Makers
MAKER_CONTEXT_MAP = [
    {
        "keys": ["torre de purga", "torres de purga", "purga de filamento", "purga", "purge tower", "wipe tower", "poop"],
        "queries": ["3d printer nozzle", "3d printing timelapse", "3d printer extruder", "3d printing"],
        "summary": "Contexto: Purga de boquilla y torre de purga -> Buscando clips de boquillas, extrusores y timelapses de capas FDM."
    },
    {
        "keys": ["bambu lab", "ams", "multicolor", "multi color", "cambio de color", "cambio de filamento"],
        "queries": ["3d printer multi color", "3d printing timelapse", "3d printer filament", "3d printing"],
        "summary": "Contexto: Impresión multicolor y AMS -> Buscando clips de cambio de filamento y timelapses a color."
    },
    {
        "keys": ["soporte", "soportes", "soportes en arbol", "tree support", "tree supports"],
        "queries": ["3d printer supports", "3d printing timelapse", "3d printer"],
        "summary": "Contexto: Estructuras de soporte -> Buscando clips de soportes y timelapses de impresión 3D."
    },
    {
        "keys": ["cama caliente", "placa pei", "cama", "adhesion", "heatbed", "pei"],
        "queries": ["3d printer bed", "3d printing surface", "3d printer leveling", "3d printer"],
        "summary": "Contexto: Cama de impresión y adhesión PEI -> Buscando clips de superficie de impresión y calibración."
    },
    {
        "keys": ["boquilla", "boquillas", "nozzle", "hotend", "atasco", "clog"],
        "queries": ["3d printer nozzle", "3d printer extruder", "3d printing close up"],
        "summary": "Contexto: Boquilla y Hotend -> Buscando macros de boquilla y cabezal de extrusión depositando plástico."
    },
    {
        "keys": ["hilos", "stringing", "retraccion", "retraction"],
        "queries": ["3d printer nozzle", "3d printer extruder", "3d printing"],
        "summary": "Contexto: Hilos y retracción -> Buscando planos cerrados de boquilla y movimientos de cabezal."
    },
    {
        "keys": ["filamento", "bobina", "spool", "pla", "petg", "tpu", "abs", "asa"],
        "queries": ["3d printing filament", "3d printer spool", "3d printing"],
        "summary": "Contexto: Filamento y bobinas -> Buscando bobinas de filamento, alimentación de material y extrusión."
    },
    {
        "keys": ["capa", "capas", "layer", "altura de capa", "resolucion"],
        "queries": ["3d printing layers", "3d printer close up", "3d printing timelapse"],
        "summary": "Contexto: Líneas de capa y resolución -> Buscando macros de capas depositándose y timelapses."
    },
    {
        "keys": ["resina", "sla", "msla", "fotopolimero", "uv"],
        "queries": ["resin 3d printer", "sla 3d printing", "3d printing"],
        "summary": "Contexto: Impresión en resina SLA -> Buscando tanques de resina líquida y curado UV."
    },
    {
        "keys": ["calibracion", "nivelacion", "leveling", "sensor"],
        "queries": ["3d printer bed leveling", "3d printer calibration", "3d printer"],
        "summary": "Contexto: Calibración y nivelación -> Buscando sensores de nivelación y ajuste de cama."
    },
    {
        "keys": ["timelapse", "time-lapse", "camara rapida"],
        "queries": ["3d printing timelapse", "3d printer timelapse", "3d printing"],
        "summary": "Contexto: Timelapse de impresión -> Buscando vídeos acelerados del objeto creciendo capa a capa."
    },
]


def expand_query_contextually(query: str, context: str = "") -> Dict[str, Any]:
    """Analiza el concepto y el contexto del canal Capa Cero para generar consultas visuales precisas en Pexels y Pixabay."""
    combined_text = f"{query} {context}".lower().strip()
    
    # 1. Buscar coincidencia en la base de conocimiento maker
    for entry in MAKER_CONTEXT_MAP:
        for key in entry["keys"]:
            if key in combined_text:
                return {
                    "queries": entry["queries"],
                    "summary": entry["summary"]
                }
                
    # 2. Si no hay coincidencia directa, limpiar y asegurar anclaje a 3D printing
    cleaned_words = [w for w in query.lower().split() if w not in {"de", "la", "el", "en", "un", "una", "los", "las", "para", "con", "por", "al", "y", "o"}]
    clean_query = " ".join(cleaned_words)
    
    if "3d" in clean_query or "impres" in clean_query:
        queries = ["3d printing", "3d printer", "3d printing timelapse"]
    else:
        queries = [f"3d printing {clean_query}", "3d printer", "3d printing timelapse"]
        
    return {
        "queries": queries[:3],
        "summary": f"Contexto Maker general: Buscando clips de '{clean_query}' anclados a maquinaria y timelapses de impresión 3D."
    }


def calculate_clip_relevance(clip: Dict[str, Any]) -> int:
    """Calcula estrictamente la relevancia del clip para garantizar contenido genuino de impresión 3D y descartar ruido."""
    text = f"{clip.get('title', '')} {clip.get('source', '')}".lower()
    
    # 1. Descarte inmediato si contiene términos de ruido
    for junk in JUNK_STOCK_TAGS:
        if junk in text:
            return -999
            
    # 2. Puntuación positiva por términos técnicos maker
    score = 0
    if "3d printer" in text or "3d printing" in text or "printer 3d" in text or "printing 3d" in text:
        score += 100
    if "3d print" in text:
        score += 90
    if "filament" in text or "nozzle" in text or "extruder" in text or "hotend" in text:
        score += 80
    if "additive manufacturing" in text or "resin 3d" in text or "sla 3d" in text:
        score += 80
    if "maker" in text or "prototyping" in text:
        score += 50
    if "timelapse" in text:
        score += 40
        
    return score


async def search_all_broll(query: str, limit: int = 80, context: str = "") -> Dict[str, Any]:
    """Busca masivamente clips en todas las plataformas con comprensión contextual y filtrado estricto."""
    config = load_config()
    pexels_key = config.get("pexels_api_key", "").strip()
    pixabay_key = config.get("pixabay_api_key", "").strip()

    # Ignorar posibles contraseñas autocompletadas por el navegador
    if pexels_key and "Seatleon" in pexels_key:
        pexels_key = ""

    context_data = expand_query_contextually(query, context)
    queries = context_data["queries"]
    summary = context_data["summary"]

    all_results = []
    seen_ids = set()

    # Búsqueda concurrente de alta velocidad (todas las consultas en paralelo con cliente compartido)
    timeout = httpx.Timeout(8.0, connect=4.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        tasks = []
        # Pexels maneja perfectamente frases descriptivas de 3 palabras
        if pexels_key:
            for q in queries[:3]:
                tasks.append(search_broll_pexels(q, pexels_key, per_page=25, client=client))

        # Pixabay requiere términos clave cortos (1-2 palabras) para no devolver ruido
        if pixabay_key:
            pix_terms = []
            for q in queries:
                short = " ".join(q.split()[:2])
                if short not in pix_terms:
                    pix_terms.append(short)
            if "3d printer" not in pix_terms:
                pix_terms.append("3d printer")

            for pq in pix_terms[:2]:
                tasks.append(search_broll_pixabay(pq, pixabay_key, per_page=20, client=client))

        if tasks:
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in batch_results:
                if isinstance(res, list):
                    for r in res:
                        if r["id"] not in seen_ids:
                            seen_ids.add(r["id"])
                            all_results.append(r)

    # Filtrar estrictamente: SOLO clips con puntuación estrictamente positiva (> 0)
    # y descartar clips con score <= 0 o negativos (-999)
    scored_clips = []
    for c in all_results:
        rel = calculate_clip_relevance(c)
        if rel > 0:
            c["relevance_score"] = rel
            scored_clips.append(c)

    # Ordenar por relevancia para que los clips más fidedignos aparezcan primero
    scored_clips.sort(key=lambda c: c["relevance_score"], reverse=True)

    # Si encontramos clips relevantes tras el filtrado estricto, usarlos
    if scored_clips:
        final_clips = scored_clips
    elif all_results:
        # Fallback ordenado si los términos eran muy abiertos
        all_results.sort(key=lambda c: calculate_clip_relevance(c), reverse=True)
        final_clips = [c for c in all_results if calculate_clip_relevance(c) >= -50]
    else:
        final_clips = []

    # Fallback demo enriquecido solo si no hay ninguna clave configurada o falló la red
    if not final_clips and not pexels_key and not pixabay_key:
        final_clips = [
            {
                "id": "demo_1",
                "source": "Stock Libre (Demo)",
                "title": "Impresora 3D imprimiendo filamento en cama caliente",
                "thumbnail": "https://images.pexels.com/photos/3862601/pexels-photo-3862601.jpeg?auto=compress&cs=tinysrgb&w=640",
                "preview_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
                "download_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
                "duration": 15,
                "width": 1920,
                "height": 1080,
                "quality": "1080p",
            },
            {
                "id": "demo_2",
                "source": "Stock Libre (Demo)",
                "title": "Detalle de boquilla extrusora depositando capas",
                "thumbnail": "https://images.pexels.com/photos/256381/pexels-photo-256381.jpeg?auto=compress&cs=tinysrgb&w=640",
                "preview_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
                "download_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
                "duration": 15,
                "width": 1920,
                "height": 1080,
                "quality": "1080p",
            },
            {
                "id": "demo_3",
                "source": "Stock Libre (Demo)",
                "title": "Taller Maker de prototipado y robótica con impresoras",
                "thumbnail": "https://images.pexels.com/photos/256381/pexels-photo-256381.jpeg?auto=compress&cs=tinysrgb&w=640",
                "preview_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
                "download_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
                "duration": 15,
                "width": 1920,
                "height": 1080,
                "quality": "1080p",
            }
        ]

    return {
        "results": final_clips[:limit],
        "context_summary": summary,
        "queries": queries,
    }



async def download_clip_file(download_url: str, output_path: Path) -> bool:
    """Descarga un clip de vídeo completo en stream para no saturar memoria."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            async with client.stream("GET", download_url) as resp:
                if resp.status_code == 200:
                    with open(output_path, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=1024 * 64):
                            f.write(chunk)
                    return True
    except Exception as e:
        print(f"Error descargando {download_url}: {e}")
    return False
