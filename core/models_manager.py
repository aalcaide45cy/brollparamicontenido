import os
import shutil
import asyncio
import threading
import time
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Any, Optional
import httpx

from core.config_manager import load_config

RECOMMENDED_MODELS = [
    {
        "id": "qwen2.5-14b",
        "name": "Qwen 2.5 14B Instruct (Motor Principal de Guiones)",
        "category": "LLMs",
        "badge": "Recomendado Guion",
        "description": "El rey en español y redacción técnica para YouTube. Especializado en redactar guiones completos con marcas de cámara [B-ROLL], ganchos adictivos y ritmo dinámico. Cabe entero en tu RTX 4090.",
        "size_gb": 8.4,
        "filename": "Qwen2.5-14B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Qwen2.5-14B-Instruct-GGUF/resolve/main/Qwen2.5-14B-Instruct-Q4_K_M.gguf",
    },
    {
        "id": "qwen2.5-7b",
        "name": "Qwen 2.5 7B Instruct (Títulos, SEO y Consultas Rápidas)",
        "category": "LLMs",
        "badge": "Ultrarrápido",
        "description": "Ultra veloz y ligero. Ideal para ideación de temas, generación instantánea de títulos de alto CTR, etiquetas SEO y respuestas en milisegundos sin sobrecargar memoria.",
        "size_gb": 4.4,
        "filename": "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q4_K_M.gguf",
    },
    {
        "id": "deepseek-r1-14b",
        "name": "DeepSeek R1 Distill Qwen 14B (Razonamiento Profundo Maker)",
        "category": "LLMs",
        "badge": "Razonamiento",
        "description": "Modelo de pensamiento paso a paso (CoT). Perfecto para resolución de problemas mecánicos complejos en impresoras 3D, tolerancias de calibración, cálculo de flujo y física de filamentos.",
        "size_gb": 8.4,
        "filename": "DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-14B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf",
    },
    {
        "id": "llama-3.1-8b",
        "name": "Meta Llama 3.1 8B Instruct (Copywriting Viral)",
        "category": "LLMs",
        "badge": "Viral / Shorts",
        "description": "Modelo de Meta optimizado en psicología de retención y copywriting. Excelente estructurando ganchos en los primeros 3 segundos para Shorts/Reels y descripciones persuasivas.",
        "size_gb": 4.6,
        "filename": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
    },
    {
        "id": "mistral-nemo-12b",
        "name": "Mistral NeMo 12B Instruct (Manuales & Contexto Largo 128K)",
        "category": "LLMs",
        "badge": "Ventana 128K",
        "description": "Colaboración Mistral AI + NVIDIA con ventana de 128.000 tokens. Capaz de analizar manuales enteros de impresoras 3D, guías de montaje de kits Voron/Prusa o transcripciones de vídeos de varias horas.",
        "size_gb": 7.0,
        "filename": "Mistral-Nemo-Instruct-2407-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Mistral-Nemo-Instruct-2407-GGUF/resolve/main/Mistral-Nemo-Instruct-2407-Q4_K_M.gguf",
    },
    {
        "id": "qwen2.5-32b",
        "name": "Qwen 2.5 32B Instruct (Máxima Calidad Documental)",
        "category": "LLMs",
        "badge": "Máxima Potencia",
        "description": "Calidad insuperable de nivel frontera. Ocupa ~18.5 GB en tu RTX 4090 (24 GB). La mayor riqueza léxica y profundidad pedagógica para vídeos largos y documentales técnicos.",
        "size_gb": 18.5,
        "filename": "Qwen2.5-32B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Qwen2.5-32B-Instruct-GGUF/resolve/main/Qwen2.5-32B-Instruct-Q4_K_M.gguf",
    },
    {
        "id": "qwen2-vl-7b",
        "name": "Qwen2-VL 7B Vision (Inspección Visual de Piezas & Slicers)",
        "category": "Vision",
        "badge": "Visión Artificial",
        "description": "Modelo de visión artificial multimodal. Puede inspeccionar fotos de piezas con defectos (stringing, warping) o capturas de Bambu Studio/OrcaSlicer para sugerir correcciones de parámetros.",
        "size_gb": 4.4,
        "filename": "Qwen2-VL-7B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Qwen2-VL-7B-Instruct-GGUF/resolve/main/Qwen2-VL-7B-Instruct-Q4_K_M.gguf",
    },
    {
        "id": "flux1-schnell-q4",
        "name": "FLUX.1 Schnell (Miniaturas Fotorrealistas en 4 Pasos)",
        "category": "ImageGen",
        "badge": "Miniaturas AI",
        "description": "El generador de imágenes de mayor calidad del mundo. Genera miniaturas hiperrealistas, renders 3D y conceptos visuales de YouTube en solo 2-4 segundos en tu RTX 4090.",
        "size_gb": 6.3,
        "filename": "flux1-schnell-Q4_K_S.gguf",
        "url": "https://huggingface.co/city96/FLUX.1-schnell-gguf/resolve/main/flux1-schnell-Q4_K_S.gguf",
    },
    {
        "id": "whisper-large-v3-turbo",
        "name": "Whisper Large v3 Turbo (Subtitulado Automático DaVinci)",
        "category": "Complementos",
        "badge": "Audio / Subtítulos",
        "description": "Transcripción de voz a texto de máxima fidelidad en español a velocidad x8. Genera archivos de subtítulos sincronizados (.srt) listos para importar a tu línea de tiempo de DaVinci Resolve.",
        "size_gb": 1.5,
        "filename": "ggml-large-v3-turbo.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin",
    },
]

# Estado global de tareas y cola de descargas
DOWNLOAD_TASKS: Dict[str, Dict[str, Any]] = {}
DOWNLOAD_QUEUE: List[str] = []
QUEUE_LOCK = threading.RLock()
IS_WORKER_ACTIVE = False


def get_models_dir() -> Path:
    config = load_config()
    path = Path(config.get("models_dir", ""))
    path.mkdir(parents=True, exist_ok=True)
    for cat in ["LLMs", "Vision", "ImageGen", "Complementos"]:
        (path / cat).mkdir(parents=True, exist_ok=True)
    return path


def format_bytes(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes / 1024**2:.1f} MB"
    else:
        return f"{size_bytes / 1024**3:.2f} GB"


def get_models_status() -> Dict[str, Any]:
    """Escanea IAsModels y devuelve estadísticas de espacio y lista de modelos instalados."""
    base_dir = get_models_dir()
    categories = ["LLMs", "Vision", "ImageGen", "Complementos"]
    
    cat_stats = {}
    installed_models = []
    total_bytes = 0

    for cat in categories:
        cat_dir = base_dir / cat
        cat_bytes = 0
        cat_files = []
        if cat_dir.exists():
            for root, _, files in os.walk(cat_dir):
                for f in files:
                    file_path = Path(root) / f
                    try:
                        sz = file_path.stat().st_size
                        cat_bytes += sz
                        total_bytes += sz
                        cat_files.append({
                            "name": f,
                            "category": cat,
                            "rel_path": str(file_path.relative_to(base_dir)),
                            "size_bytes": sz,
                            "size_formatted": format_bytes(sz),
                        })
                    except Exception:
                        pass
        cat_stats[cat] = {
            "bytes": cat_bytes,
            "formatted": format_bytes(cat_bytes),
            "count": len(cat_files),
            "files": cat_files,
        }
        installed_models.extend(cat_files)

    recommended_status = []
    for rec in RECOMMENDED_MODELS:
        target = base_dir / rec["category"] / rec["filename"]
        installed = target.exists() and target.stat().st_size > 1024 * 1024
        download_info = DOWNLOAD_TASKS.get(rec["id"], None)
        status_str = download_info.get("status") if download_info else None

        recommended_status.append({
            **rec,
            "installed": installed,
            "installed_size": format_bytes(target.stat().st_size) if installed else "0 GB",
            "downloading": status_str == "downloading",
            "queued": status_str == "queued",
            "download_percent": download_info.get("percent", 0) if download_info else 0,
            "speed": download_info.get("speed_mb", "") if download_info else "",
            "eta": download_info.get("eta", "") if download_info else "",
        })

    return {
        "models_dir": str(base_dir),
        "total_bytes": total_bytes,
        "total_formatted": format_bytes(total_bytes),
        "categories": cat_stats,
        "installed_models": installed_models,
        "recommended": recommended_status,
        "queue_length": len(DOWNLOAD_QUEUE),
    }


def delete_model_file(category: str, filename: str) -> bool:
    """Elimina un modelo específico para liberar espacio."""
    base_dir = get_models_dir()
    target = base_dir / category / filename
    if target.exists() and target.is_file():
        target.unlink()
        return True
    return False


def purge_category(category: str) -> int:
    """Elimina todos los archivos de una subcarpeta específica."""
    base_dir = get_models_dir()
    cat_dir = base_dir / category
    count = 0
    if cat_dir.exists():
        for item in cat_dir.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                    count += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    count += 1
            except Exception:
                pass
    return count


def _download_part(cdn_url: str, start: int, end: int, temp_path: Path, progress_callback):
    """Descarga un rango específico de bytes en paralelo directamente desde la CDN de Hugging Face."""
    headers = {"Range": f"bytes={start}-{end}"}
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        with client.stream("GET", cdn_url, headers=headers) as resp:
            if resp.status_code not in (200, 206):
                raise RuntimeError(f"HTTP {resp.status_code} al descargar rango {start}-{end}")
            pos = start
            with open(temp_path, "r+b") as f:
                for chunk in resp.iter_bytes(chunk_size=1024 * 1024 * 2):  # Buffers de 2 MB
                    if chunk:
                        f.seek(pos)
                        f.write(chunk)
                        pos += len(chunk)
                        progress_callback(len(chunk))


def _fast_download_worker(model_id: str, url: str, target_path: Path):
    """Worker de descarga ultrarrápida multihilo con estimación de velocidad y ETA."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(".downloading")

    try:
        DOWNLOAD_TASKS[model_id] = {
            "status": "downloading",
            "percent": 0,
            "downloaded": 0,
            "total": 0,
            "speed_mb": "Iniciando...",
            "eta": "Calculando..."
        }

        # 1. Resolver redirección directa a la CDN
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            head_resp = client.head(url)
            cdn_url = str(head_resp.url)
            total = int(head_resp.headers.get("content-length", 0))
            accept_ranges = head_resp.headers.get("accept-ranges") == "bytes"

        if total <= 0:
            raise RuntimeError("No se pudo determinar el tamaño del archivo en Hugging Face")

        # 2. Pre-asignar archivo temporal
        with open(temp_path, "wb") as f:
            f.seek(total - 1)
            f.write(b"\0")

        # Métricas de velocidad
        downloaded_bytes = 0
        lock = threading.Lock()
        start_time = time.time()
        last_time = start_time
        last_bytes = 0
        speed_str = "0.0 MB/s"
        eta_str = "Calculando..."

        def on_chunk(chunk_len):
            nonlocal downloaded_bytes, last_time, last_bytes, speed_str, eta_str
            with lock:
                downloaded_bytes += chunk_len
                now = time.time()
                dt = now - last_time
                if dt >= 1.0:
                    speed_bps = (downloaded_bytes - last_bytes) / dt
                    last_bytes = downloaded_bytes
                    last_time = now
                    speed_mb = speed_bps / (1024 * 1024)
                    speed_str = f"{speed_mb:.1f} MB/s"
                    remaining = total - downloaded_bytes
                    if speed_bps > 0:
                        rem_sec = int(remaining / speed_bps)
                        eta_str = f"{rem_sec // 60}m {rem_sec % 60}s" if rem_sec >= 60 else f"{rem_sec}s"

                pct = int((downloaded_bytes / total) * 100) if total > 0 else 0
                DOWNLOAD_TASKS[model_id] = {
                    "status": "downloading",
                    "percent": min(pct, 99),
                    "downloaded": downloaded_bytes,
                    "total": total,
                    "speed_mb": speed_str,
                    "eta": eta_str
                }

        # 3. Descarga simultánea en 8 hilos si soporta Range, o 1 hilo si no
        num_workers = 8 if accept_ranges else 1
        part_size = total // num_workers
        ranges = []
        for i in range(num_workers):
            r_start = i * part_size
            r_end = (i + 1) * part_size - 1 if i < num_workers - 1 else total - 1
            ranges.append((r_start, r_end))

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(_download_part, cdn_url, r[0], r[1], temp_path, on_chunk)
                for r in ranges
            ]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        # 4. Renombrar al archivo final al completar
        if temp_path.exists():
            if target_path.exists():
                target_path.unlink()
            temp_path.rename(target_path)
            DOWNLOAD_TASKS[model_id] = {
                "status": "completed",
                "percent": 100,
                "downloaded": total,
                "total": total,
                "speed_mb": "Completado",
                "eta": "0s"
            }
    except Exception as e:
        DOWNLOAD_TASKS[model_id] = {"status": "error", "error": str(e), "percent": 0}
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
    finally:
        _process_next_in_queue()


def _process_next_in_queue():
    """Procesa el siguiente modelo de la cola."""
    global IS_WORKER_ACTIVE
    next_model_id = None
    with QUEUE_LOCK:
        if not DOWNLOAD_QUEUE:
            IS_WORKER_ACTIVE = False
            return
        next_model_id = DOWNLOAD_QUEUE.pop(0)
        IS_WORKER_ACTIVE = True

    model_info = next((m for m in RECOMMENDED_MODELS if m["id"] == next_model_id), None)
    if model_info:
        base_dir = get_models_dir()
        target = base_dir / model_info["category"] / model_info["filename"]
        thread = threading.Thread(
            target=_fast_download_worker,
            args=(next_model_id, model_info["url"], target),
            daemon=True
        )
        thread.start()
    else:
        _process_next_in_queue()


def start_model_download(model_id: str) -> bool:
    """Añade un modelo a la cola de descarga y la inicia si no hay otra en marcha."""
    global IS_WORKER_ACTIVE
    model_info = next((m for m in RECOMMENDED_MODELS if m["id"] == model_id), None)
    if not model_info:
        return False

    should_start = False
    with QUEUE_LOCK:
        current_status = DOWNLOAD_TASKS.get(model_id, {}).get("status")
        if current_status not in ("downloading", "queued"):
            DOWNLOAD_QUEUE.append(model_id)
            DOWNLOAD_TASKS[model_id] = {
                "status": "queued",
                "percent": 0,
                "speed_mb": "En cola",
                "eta": "Esperando turno"
            }

        if not IS_WORKER_ACTIVE:
            should_start = True

    if should_start:
        _process_next_in_queue()
    return True


def download_all_models() -> List[str]:
    """Añade todos los modelos recomendados no instalados a la cola de descarga rápida."""
    base_dir = get_models_dir()
    queued = []
    for m in RECOMMENDED_MODELS:
        target = base_dir / m["category"] / m["filename"]
        installed = target.exists() and target.stat().st_size > 1024 * 1024
        if not installed:
            start_model_download(m["id"])
            queued.append(m["id"])
    return queued
