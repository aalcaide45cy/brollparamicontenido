import os
import shutil
import asyncio
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
import httpx

from core.config_manager import load_config

RECOMMENDED_MODELS = [
    {
        "id": "qwen2.5-14b",
        "name": "Qwen 2.5 14B Instruct (Recomendado)",
        "category": "LLMs",
        "description": "Excelente en español, redacción técnica y guiones virales. Cabe entero en la RTX 4090.",
        "size_gb": 9.0,
        "filename": "qwen2.5-14b-instruct-q4_k_m.gguf",
        "url": "https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/resolve/main/qwen2.5-14b-instruct-q4_k_m.gguf",
    },
    {
        "id": "qwen2.5-7b",
        "name": "Qwen 2.5 7B Instruct (Rápido / Ligero)",
        "category": "LLMs",
        "description": "Ultrarrápido para respuestas instantáneas de guion y consultas breves.",
        "size_gb": 4.7,
        "filename": "qwen2.5-7b-instruct-q4_k_m.gguf",
        "url": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf",
    },
    {
        "id": "llama-3.1-8b",
        "name": "Llama 3.1 8B Instruct",
        "category": "LLMs",
        "description": "Modelo versátil de Meta, muy bueno estructurando ganchos y retención.",
        "size_gb": 4.9,
        "filename": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
    },
    {
        "id": "flux1-schnell-q4",
        "name": "FLUX.1 Schnell (Miniaturas en 4 pasos)",
        "category": "ImageGen",
        "description": "Generación hiperrealista de miniaturas y renders 3D en 2-4 segundos en tu RTX 4090.",
        "size_gb": 11.2,
        "filename": "flux1-schnell-q4_k_s.gguf",
        "url": "https://huggingface.co/city96/FLUX.1-schnell-gguf/resolve/main/flux1-schnell-q4_k_s.gguf",
    },
]

# Estado global de descargas en segundo plano
DOWNLOAD_TASKS: Dict[str, Dict[str, Any]] = {}


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
        recommended_status.append({
            **rec,
            "installed": installed,
            "installed_size": format_bytes(target.stat().st_size) if installed else "0 GB",
            "downloading": download_info.get("status") == "downloading" if download_info else False,
            "download_percent": download_info.get("percent", 0) if download_info else 0,
        })

    return {
        "models_dir": str(base_dir),
        "total_bytes": total_bytes,
        "total_formatted": format_bytes(total_bytes),
        "categories": cat_stats,
        "installed_models": installed_models,
        "recommended": recommended_status,
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


def _download_worker(model_id: str, url: str, target_path: Path):
    try:
        DOWNLOAD_TASKS[model_id] = {"status": "downloading", "percent": 0, "downloaded": 0, "total": 0}
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_path.with_suffix(".downloading")

        with httpx.Client(timeout=None, follow_redirects=True) as client:
            with client.stream("GET", url) as resp:
                if resp.status_code != 200:
                    DOWNLOAD_TASKS[model_id] = {"status": "error", "error": f"HTTP {resp.status_code}"}
                    return
                
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0
                with open(temp_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=1024 * 512):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            percent = int((downloaded / total) * 100) if total > 0 else 0
                            DOWNLOAD_TASKS[model_id] = {
                                "status": "downloading",
                                "percent": percent,
                                "downloaded": downloaded,
                                "total": total,
                            }
        
        if temp_path.exists():
            temp_path.rename(target_path)
            DOWNLOAD_TASKS[model_id] = {"status": "completed", "percent": 100}
    except Exception as e:
        DOWNLOAD_TASKS[model_id] = {"status": "error", "error": str(e)}


def start_model_download(model_id: str) -> bool:
    """Inicia la descarga de un modelo recomendado en segundo plano."""
    model_info = next((m for m in RECOMMENDED_MODELS if m["id"] == model_id), None)
    if not model_info:
        return False
    
    base_dir = get_models_dir()
    target = base_dir / model_info["category"] / model_info["filename"]
    
    thread = threading.Thread(
        target=_download_worker,
        args=(model_id, model_info["url"], target),
        daemon=True
    )
    thread.start()
    return True
