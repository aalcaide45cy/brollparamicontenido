import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from core.config_manager import load_config, save_config
from core.models_manager import (
    get_models_status,
    start_model_download,
    delete_model_file,
    purge_category,
)
from services.ai_service import (
    generate_full_script,
    generate_titles_suite,
    generate_thumbnails_suite,
    generate_seo_suite,
)
from services.broll_service import (
    search_all_broll,
    download_clip_file,
    clean_filename,
)
from services.project_service import (
    create_project_bundle,
    open_folder_in_explorer,
    list_recent_projects,
)

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="Estudio de Preproducción Capa Cero", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === MODELOS PYDANTIC ===
class ScriptRequest(BaseModel):
    topic: str
    content_type: str = "short"
    duration_sec: int = 60
    context: str = ""


class TitlesRequest(BaseModel):
    topic: str
    context: str = ""


class ThumbnailsRequest(BaseModel):
    topic: str


class SeoRequest(BaseModel):
    topic: str
    script_summary: str = ""


class BrollSearchRequest(BaseModel):
    query: str
    limit: int = 20


class BrollDownloadRequest(BaseModel):
    project_path: str
    clips: List[Dict[str, Any]]


class AutoBrollRequest(BaseModel):
    project_path: str
    query: str
    count: int = 6


class CreateProjectRequest(BaseModel):
    topic: str
    script: str = ""
    titles: str = ""
    thumbnails: str = ""
    seo: str = ""


class OpenFolderRequest(BaseModel):
    path: str


class ModelActionRequest(BaseModel):
    model_id: Optional[str] = None
    category: Optional[str] = None
    filename: Optional[str] = None


# === ENDPOINTS CONFIGURACIÓN ===
@app.get("/api/config")
async def get_config_endpoint():
    return load_config()


@app.post("/api/config")
async def update_config_endpoint(config_data: Dict[str, Any]):
    updated = save_config(config_data)
    return {"status": "ok", "config": updated}


# === ENDPOINTS MODELOS IA (IAsModels) ===
@app.get("/api/models/status")
async def models_status_endpoint():
    return get_models_status()


@app.post("/api/models/download")
async def models_download_endpoint(req: ModelActionRequest):
    if not req.model_id:
        raise HTTPException(status_code=400, detail="model_id requerido")
    success = start_model_download(req.model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Modelo no encontrado en la lista recomendada")
    return {"status": "started", "model_id": req.model_id}


@app.post("/api/models/delete")
async def models_delete_endpoint(req: ModelActionRequest):
    if not req.category or not req.filename:
        raise HTTPException(status_code=400, detail="category y filename requeridos")
    deleted = delete_model_file(req.category, req.filename)
    return {"status": "ok", "deleted": deleted}


@app.post("/api/models/purge")
async def models_purge_endpoint(req: ModelActionRequest):
    if not req.category:
        raise HTTPException(status_code=400, detail="category requerida")
    count = purge_category(req.category)
    return {"status": "ok", "purged_count": count}


# === ENDPOINTS IA (GUION, TÍTULOS, MINIATURAS, SEO) ===
@app.post("/api/script/generate")
async def generate_script_endpoint(req: ScriptRequest):
    try:
        res = await generate_full_script(
            topic=req.topic,
            content_type=req.content_type,
            duration_sec=req.duration_sec,
            context=req.context,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/titles/generate")
async def generate_titles_endpoint(req: TitlesRequest):
    try:
        res = await generate_titles_suite(topic=req.topic, context=req.context)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/thumbnails/generate")
async def generate_thumbnails_endpoint(req: ThumbnailsRequest):
    try:
        res = await generate_thumbnails_suite(topic=req.topic)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/seo/generate")
async def generate_seo_endpoint(req: SeoRequest):
    try:
        res = await generate_seo_suite(topic=req.topic, script_summary=req.script_summary)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === ENDPOINTS B-ROLL (PEXELS / PIXABAY) ===
@app.post("/api/broll/search")
async def search_broll_endpoint(req: BrollSearchRequest):
    try:
        results = await search_all_broll(query=req.query, limit=req.limit)
        return {"query": req.query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/broll/download")
async def download_selected_broll(req: BrollDownloadRequest):
    """Descarga los clips seleccionados a la carpeta del proyecto."""
    dest_dir = Path(req.project_path) / "BRoll_Videos"
    dest_dir.mkdir(parents=True, exist_ok=True)

    downloaded = []
    failed = []

    for idx, clip in enumerate(req.clips):
        url = clip.get("download_url")
        if not url:
            continue
        title = clean_filename(clip.get("title", f"clip_{idx+1}"))
        source = clip.get("source", "stock").lower().replace(" ", "_")
        target_name = f"{idx+1:02d}_{source}_{title}.mp4"
        target_file = dest_dir / target_name

        success = await download_clip_file(url, target_file)
        if success:
            downloaded.append({"title": title, "path": str(target_file)})
        else:
            failed.append(title)

    return {
        "status": "completed",
        "downloaded_count": len(downloaded),
        "failed_count": len(failed),
        "downloaded": downloaded,
    }


@app.post("/api/broll/download-best")
async def auto_download_best_broll(req: AutoBrollRequest):
    """Busca y descarga automáticamente los mejores N clips de recurso."""
    dest_dir = Path(req.project_path) / "BRoll_Videos"
    dest_dir.mkdir(parents=True, exist_ok=True)

    results = await search_all_broll(query=req.query, limit=req.count + 5)
    best_clips = results[:req.count]

    downloaded = []
    for idx, clip in enumerate(best_clips):
        url = clip.get("download_url")
        if not url:
            continue
        title = clean_filename(clip.get("title", f"broll_{idx+1}"))
        source = clip.get("source", "stock").lower().replace(" ", "_")
        target_name = f"auto_{idx+1:02d}_{source}_{title}.mp4"
        target_file = dest_dir / target_name

        ok = await download_clip_file(url, target_file)
        if ok:
            downloaded.append({"title": title, "path": str(target_file)})

    return {
        "status": "completed",
        "downloaded_count": len(downloaded),
        "downloaded": downloaded,
    }


# === ENDPOINTS PROYECTOS PARA DAVINCI RESOLVE ===
@app.post("/api/projects/create")
async def create_project_endpoint(req: CreateProjectRequest):
    try:
        bundle = create_project_bundle(
            topic=req.topic,
            script=req.script,
            titles=req.titles,
            thumbnails=req.thumbnails,
            seo=req.seo,
        )
        return {"status": "ok", "bundle": bundle}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/list")
async def list_projects_endpoint():
    return list_recent_projects()


@app.post("/api/projects/open")
async def open_folder_endpoint(req: OpenFolderRequest):
    opened = open_folder_in_explorer(req.path)
    return {"status": "ok", "opened": opened}


# === FRONTEND ESTÁTICO ===
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(WEB_DIR / "index.html"))


if __name__ == "__main__":
    # Vinculación estricta a 127.0.0.1 (Localhost) para evitar alertas del Firewall de Windows
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

