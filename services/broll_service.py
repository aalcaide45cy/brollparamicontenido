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


# Glosario de traducción rápida para bancos de stock en inglés
STOCK_TRANSLATION_MAP = {
    "impresora 3d": "3d printer",
    "impresion 3d": "3d printing",
    "imprimiendo": "3d printing timelapse",
    "soporte": "support tree",
    "soportes": "tree supports 3d printing",
    "soportes en arbol": "tree support 3d printing",
    "cama caliente": "heated bed build plate",
    "placa pei": "pei sheet build plate",
    "boquilla": "3d printer nozzle",
    "boquillas": "brass nozzle extruder",
    "filamento": "3d printing filament spool",
    "extrusor": "direct drive extruder",
    "atasco": "clogged extruder nozzle",
    "purga": "filament purge poop",
    "resina": "resin 3d printer",
    "calibracion": "bed leveling 3d printer",
    "taller": "maker lab workshop 3d printer",
    "robotica": "robotics engineering technology",
    "tecnologia": "modern technology high tech",
    "ordenador": "computer cad design 3d model",
    "diseno": "cad 3d design modeling",
}


def expand_query_multilingual(query: str) -> List[str]:
    """Expande y traduce la consulta a inglés para encontrar x10 más vídeos en Pexels y Pixabay."""
    queries = [query.strip()]
    q_lower = query.lower().strip()

    # Reemplazo de frases compuestas primero (orden descendente por longitud)
    expanded_english = q_lower
    has_match = False
    sorted_terms = sorted(STOCK_TRANSLATION_MAP.items(), key=lambda x: len(x[0]), reverse=True)
    for es_term, en_term in sorted_terms:
        if es_term in expanded_english:
            expanded_english = expanded_english.replace(es_term, en_term)
            has_match = True

    if has_match and expanded_english != q_lower:
        queries.append(expanded_english)

    # Si la consulta no tiene "3d printer" y es técnica, añadir variante contextual
    if any(k in q_lower for k in ["filamento", "cama", "soporte", "boquilla", "purga", "capa", "nozzle"]):
        if "3d" not in expanded_english:
            queries.append(f"3d printing {expanded_english}")

    return list(dict.fromkeys(queries))


async def search_all_broll(query: str, limit: int = 80) -> List[Dict[str, Any]]:
    """Busca masivamente clips en todas las plataformas combinando términos en español e inglés."""
    config = load_config()
    pexels_key = config.get("pexels_api_key", "").strip()
    pixabay_key = config.get("pixabay_api_key", "").strip()

    queries = expand_query_multilingual(query)
    all_results = []
    seen_ids = set()

    for q in queries:
        # Búsqueda en Pexels (hasta 50 por término)
        if pexels_key:
            p_res = await search_broll_pexels(q, pexels_key, per_page=40)
            for r in p_res:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    all_results.append(r)

        # Búsqueda en Pixabay (hasta 50 por término)
        if pixabay_key:
            px_res = await search_broll_pixabay(q, pixabay_key, per_page=40)
            for r in px_res:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    all_results.append(r)

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
