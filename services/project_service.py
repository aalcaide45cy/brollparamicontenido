import os
import re
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.config_manager import load_config


def sanitize_folder_name(name: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    cleaned = cleaned.strip().replace(" ", "_")
    return cleaned[:50]


def get_projects_root() -> Path:
    config = load_config()
    p = Path(config.get("download_path", ""))
    p.mkdir(parents=True, exist_ok=True)
    return p


def create_project_bundle(
    topic: str,
    script: str = "",
    titles: str = "",
    thumbnails: str = "",
    seo: str = "",
) -> Dict[str, Any]:
    """Crea la estructura organizada de carpetas para DaVinci Resolve y guarda todos los textos."""
    root = get_projects_root()
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    folder_name = f"{date_str}_{sanitize_folder_name(topic)}"
    project_dir = root / folder_name

    broll_dir = project_dir / "BRoll_Videos"
    miniaturas_dir = project_dir / "Miniaturas"
    guiones_dir = project_dir / "Guiones"

    for d in [broll_dir, miniaturas_dir, guiones_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Guardar Guion
    if script:
        with open(guiones_dir / "guion_principal.txt", "w", encoding="utf-8") as f:
            f.write(script)

    # 2. Guardar Titulos y Miniaturas
    if thumbnails:
        with open(miniaturas_dir / "prompts_miniatura.txt", "w", encoding="utf-8") as f:
            f.write(thumbnails)

    # 3. Guardar Paquete Completo SEO para YouTube
    seo_content = []
    seo_content.append(f"=== PROYECTO: {topic} ===")
    seo_content.append(f"Fecha de Creación: {date_str}\n")
    if titles:
        seo_content.append("--- TÍTULOS DE ALTO CTR ---")
        seo_content.append(titles.strip() + "\n")
    if seo:
        seo_content.append("--- DESCRIPCIÓN, METADATOS Y TAGS ---")
        seo_content.append(seo.strip() + "\n")

    with open(project_dir / "YouTube_SEO.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(seo_content))

    return {
        "project_name": folder_name,
        "project_path": str(project_dir),
        "broll_dir": str(broll_dir),
        "miniaturas_dir": str(miniaturas_dir),
        "guiones_dir": str(guiones_dir),
        "seo_file": str(project_dir / "YouTube_SEO.txt"),
    }


def open_folder_in_explorer(folder_path: str) -> bool:
    """Abre la carpeta en el Explorador de archivos de Windows."""
    try:
        p = Path(folder_path)
        if p.exists():
            os.startfile(str(p))
            return True
    except Exception as e:
        print(f"Error abriendo carpeta en Explorer: {e}")
    return False


def list_recent_projects() -> List[Dict[str, Any]]:
    """Devuelve la lista de proyectos guardados en el disco con conteo de archivos."""
    root = get_projects_root()
    projects = []
    if not root.exists():
        return []

    for item in sorted(root.iterdir(), reverse=True):
        if item.is_dir():
            broll_count = 0
            broll_dir = item / "BRoll_Videos"
            if broll_dir.exists():
                broll_count = len([f for f in broll_dir.iterdir() if f.is_file()])

            projects.append({
                "name": item.name,
                "path": str(item),
                "modified": datetime.datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                "broll_count": broll_count,
            })
    return projects
