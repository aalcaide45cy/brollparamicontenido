import re
import os
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.config_manager import load_config

PEXELS_VIDEOS_URL = "https://api.pexels.com/videos/search"
PIXABAY_VIDEOS_URL = "https://pixabay.com/api/videos/"


def clean_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    return cleaned.strip().replace(" ", "_")[:60]


async def search_broll_pexels(query: str, api_key: str, per_page: int = 15) -> List[Dict[str, Any]]:
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
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(PEXELS_VIDEOS_URL, headers=headers, params=params)
            if resp.status_code == 200:
                data = resp.json()
                for v in data.get("videos", []):
                    # Buscar el video file de mayor calidad
                    video_files = v.get("video_files", [])
                    if not video_files:
                        continue
                    
                    # Ordenar por ancho descendente
                    video_files.sort(key=lambda x: x.get("width", 0), reverse=True)
                    best_file = video_files[0]
                    # Buscar preview más ligero para hover
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
        print(f"Error buscando en Pexels: {e}")
    return results


async def search_broll_pixabay(query: str, api_key: str, per_page: int = 15) -> List[Dict[str, Any]]:
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
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(PIXABAY_VIDEOS_URL, params=params)
            if resp.status_code == 200:
                data = resp.json()
                for hit in data.get("hits", []):
                    videos = hit.get("videos", {})
                    # Preferir large o medium
                    best = videos.get("large") or videos.get("medium") or videos.get("small")
                    preview = videos.get("tiny") or videos.get("small") or best
                    
                    if not best:
                        continue

                    results.append({
                        "id": f"pixabay_{hit.get('id')}",
                        "source": "Pixabay",
                        "title": hit.get("tags", f"Clip {hit.get('id')}"),
                        "thumbnail": f"https://i.vimeocdn.com/video/{hit.get('picture_id')}_640x360.jpg",
                        "preview_url": preview.get("url", ""),
                        "download_url": best.get("url", ""),
                        "duration": hit.get("duration", 0),
                        "width": best.get("width", 1920),
                        "height": best.get("height", 1080),
                        "quality": f"{best.get('width')}x{best.get('height')}",
                    })
    except Exception as e:
        print(f"Error buscando en Pixabay: {e}")
    return results


# Stop words en espanol para no enviar conectores vacios a APIs en ingles
SPANISH_STOP_WORDS = {
    "de", "del", "la", "el", "en", "un", "una", "los", "las", "para",
    "con", "por", "al", "sobre", "y", "o", "un", "su", "sus", "como"
}

# Mapeo semantico de conceptos tecnicos maker a terminos de busqueda optimos para Pexels y Pixabay
CONCEPT_SEARCH_MAP = {
    "purga de filamento": ["3d printer filament", "3d printer nozzle", "3d printing"],
    "purga": ["3d printer filament", "3d printer nozzle", "3d printing"],
    "filamento": ["3d printer filament", "3d printing filament", "3d printer"],
    "impresora 3d": ["3d printer", "3d printing timelapse"],
    "impresion 3d": ["3d printing", "3d printer close up"],
    "imprimiendo": ["3d printing timelapse", "3d printer"],
    "boquilla": ["3d printer nozzle", "3d printer extruder"],
    "boquillas": ["3d printer nozzle", "3d printer extruder"],
    "cama caliente": ["3d printer bed", "3d printing surface"],
    "placa pei": ["3d printer bed", "3d printing"],
    "soporte": ["3d printer supports", "3d printing"],
    "soportes": ["3d printer supports", "3d printing"],
    "soportes en arbol": ["tree supports 3d printing", "3d printer"],
    "extrusor": ["3d printer extruder", "direct drive extruder"],
    "atasco": ["3d printer nozzle", "3d printer extruder"],
    "resina": ["resin 3d printer", "sla 3d printing"],
    "calibracion": ["3d printer bed leveling", "3d printer calibration"],
    "timelapse": ["3d printer timelapse", "3d printing timelapse"],
    "taller": ["maker lab 3d printer", "maker workshop"],
    "robotica": ["robotics engineering", "robot arm technology"],
    "tecnologia": ["modern technology", "engineering lab"],
}


def expand_query_multilingual(query: str) -> List[str]:
    """Expande la consulta en espanol hacia terminos precisos en ingles para Pexels y Pixabay."""
    q_lower = query.lower().strip()
    queries: List[str] = []

    # 1. Detectar conceptos maker prioritarios (frases largas primero)
    for es_term, en_list in sorted(CONCEPT_SEARCH_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if es_term in q_lower:
            for item in en_list:
                if item not in queries:
                    queries.append(item)

    # 2. Si no hubo coincidencia directa en el mapa, limpiar conectores en espanol
    if not queries:
        words = [w for w in q_lower.split() if w not in SPANISH_STOP_WORDS]
        cleaned = " ".join(words)
        if cleaned:
            queries.append(cleaned)
            if "3d" not in cleaned:
                queries.append(f"3d printing {cleaned}")

    # Asegurar un maximo de 3 consultas muy enfocadas
    return queries[:3]


def calculate_clip_relevance(clip: Dict[str, Any], original_query: str) -> int:
    """Calcula la relevancia del clip para priorizar videos reales de impresion 3D y descartar ruido."""
    tags = str(clip.get("title", "")).lower()
    score = 0

    # Palabras clave de alta relevancia en impresion 3D
    if "3d printer" in tags or "3d printing" in tags:
        score += 50
    if "printer" in tags and "3d" in tags:
        score += 40
    if "filament" in tags or "nozzle" in tags or "extruder" in tags:
        score += 35
    if "maker" in tags or "engineering" in tags:
        score += 20
    if "machine" in tags or "robot" in tags or "technology" in tags:
        score += 10

    # Ruido tipico devuelto por Pixabay cuando no hay coincidencia exacta
    bad_tags = ["earth", "planet", "wormhole", "space", "galaxy", "light bulb", "bulb", "lamp", "skull", "skeleton", "candle"]
    if any(b in tags for b in bad_tags):
        score -= 80

    return score


async def search_all_broll(query: str, limit: int = 80) -> List[Dict[str, Any]]:
    """Busca masivamente clips en todas las plataformas combinando terminos tecnicos precisos."""
    config = load_config()
    pexels_key = config.get("pexels_api_key", "").strip()
    pixabay_key = config.get("pixabay_api_key", "").strip()

    # Ignorar posibles contrasenas autocompletadas por el navegador
    if pexels_key and "Seatleon" in pexels_key:
        pexels_key = ""

    queries = expand_query_multilingual(query)
    all_results = []
    seen_ids = set()

    for q in queries:
        # Busqueda en Pexels (hasta 40 por termino)
        if pexels_key:
            p_res = await search_broll_pexels(q, pexels_key, per_page=40)
            for r in p_res:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    all_results.append(r)

        # Busqueda en Pixabay (hasta 40 por termino)
        if pixabay_key:
            px_res = await search_broll_pixabay(q, pixabay_key, per_page=40)
            for r in px_res:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    all_results.append(r)

    # Ordenar por relevancia para que los clips reales de impresion 3D aparezcan primero
    all_results.sort(key=lambda c: calculate_clip_relevance(c, query), reverse=True)

    # Filtrar clips que tengan score fuertemente negativo (ruido espacial/bombillas)
    filtered = [c for c in all_results if calculate_clip_relevance(c, query) >= 0]
    if filtered:
        all_results = filtered

    # Fallback demo enriquecido si no hay claves configuradas
    if not all_results:
        all_results = [
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

    return all_results[:limit]



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
