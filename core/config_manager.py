import json
import os
from pathlib import Path
from typing import Dict, Any

DEFAULT_CONFIG: Dict[str, Any] = {
    "download_path": str(Path(__file__).resolve().parent.parent / "Proyectos_YouTube"),
    "models_dir": str(Path(__file__).resolve().parent.parent / "IAsModels"),
    "gemini_api_key": "",
    "pexels_api_key": "",
    "pixabay_api_key": "",
    "ai_provider": "gemini",
    "local_llm_endpoint": "http://127.0.0.1:8080/v1",
    "local_model_name": "qwen2.5-14b-instruct",
    "broll_quality": "1080p",
    "words_per_minute": 140,
    "youtube_fixed_template": (
        "\n\n--- REDES Y COMUNIDAD ---\n"
        "📢 Canal de Telegram / Discord: https://...\n"
        "📸 Instagram / TikTok: @capacero\n"
        "\n--- FILAMENTOS Y MATERIALES RECOMENDADOS ---\n"
        "🛒 Filamento PLA de confianza: https://...\n"
        "🛒 Boquillas y recambios: https://...\n"
    ),
    "language_tone": "es-ES",
}

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"


def load_config() -> Dict[str, Any]:
    """Carga la configuracion desde config.json o crea la predeterminada."""
    if not CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"Error cargando config.json: {e}. Usando valores por defecto.")
        return DEFAULT_CONFIG.copy()


def save_config(new_config: Dict[str, Any]) -> Dict[str, Any]:
    """Guarda la configuracion actualizada en config.json."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = DEFAULT_CONFIG.copy()
    else:
        config = DEFAULT_CONFIG.copy()

    config.update(new_config)
    
    download_dir = Path(config.get("download_path", ""))
    if download_dir:
        try:
            download_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    return config

