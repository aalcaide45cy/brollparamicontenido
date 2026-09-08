# Capa Cero - Estudio de Preproducción de Contenido YouTube & B-Roll AI 🎬🚀

Aplicación autónoma local diseñada para optimizar al 100% la creación de contenido técnico y viral para YouTube (Shorts y vídeos horizontales en 16:9 sobre impresión 3D y tecnología), pensada para trabajar mano a mano con **DaVinci Resolve** y acelerada por hardware en **AMD Ryzen 9 9950X3D + NVIDIA RTX 4090 (24 GB VRAM)**.

---

## 🌟 Características Principales

1. **Guiones Inteligentes con Fact-Checking:**
   * Generación de guiones en español natural con jerga técnica real de taller (slicers, camas PEI, voladizos, distancias Z de contacto, retracciones).
   * Verificación técnica mediante **Google Search Grounding** para evitar datos alucinados o temperaturas erróneas.
   * Modos para Shorts (30s, 60s, 90s, 120s) y vídeos largos horizontales con marcas de retención y B-Roll `[B-ROLL: ...]`.

2. **B-Roll Hub Libre de Derechos (Pexels / Pixabay):**
   * Buscador de clips y fotos en alta resolución (4K y 1080p) con licencia comercial gratuita.
   * Previsualización de vídeo en bucle al pasar el ratón (hover) sobre cada tarjeta.
   * **Doble modo de descarga:**
     * *Descargar los mejores automáticamente:* Descarga los 6 mejores clips directamente a la carpeta de DaVinci.
     * *Explorar y elegir manualmente:* Marca los clips deseados con casillas de verificación y descárgalos en lote.
   * Vídeos completos en formato MP4 original listos para importar a DaVinci Resolve (sin recortes automáticos que arruinen el ritmo de edición).

3. **Suite de Viralidad y CTR:**
   * **12 Títulos de Alto CTR** organizados en 4 categorías probadas (Curiosidad, Problema/Solución, Polémica, SEO).
   * **4 Propuestas de Miniatura** con prompts listos para copiar a ChatGPT/Midjourney (con espacio reservado para la silueta del creador o composiciones a pantalla completa).
   * **Caja de Herramientas SEO:** Descripción combinada con tu plantilla fija de afiliados/redes, marcas de tiempo/capítulos automáticos, tags y hashtags.

4. **Aislamiento Total ("Cero Basura en el PC"):**
   * El entorno virtual vive exclusivamente en `.venv/`.
   * Los modelos de inteligencia artificial se almacenan en `IAsModels/` (`LLMs/`, `Vision/`, `ImageGen/`, `Complementos/`).
   * Redirección de variables de caché para que ningún modelo escriba archivos ocultos en `C:\Users\...\.cache`.
   * Pestaña **Gestor de Modelos** para monitorizar espacio en disco y eliminar o restaurar modelos en 1 clic.
   * Configuración persistente en `config.json` para no reintroducir rutas ni claves tras reiniciar.

---

## 🚀 Arranque Rápido

Haz doble clic en el archivo:
```bash
iniciar.bat
```
El script activará el entorno virtual `.venv`, redirigirá las cachés de IA a `IAsModels` y abrirá automáticamente tu navegador en `http://127.0.0.1:8000`.

---

## 📁 Estructura del Proyecto para DaVinci Resolve

Cada proyecto creado genera una carpeta organizada automáticamente en tu ruta configurada:
```text
Proyectos_YouTube/
  └── 2026-09_Guia_Soportes_3D/
        ├── BRoll_Videos/         # Clips MP4 listos para la línea de tiempo de DaVinci
        ├── Miniaturas/           # Prompts e imágenes conceptuales
        ├── Guiones/              # Guion de locución (.txt)
        └── YouTube_SEO.txt       # Títulos, descripción completa, capítulos y tags
```

---

## 🔑 Claves de API Gratuitas

La aplicación funciona de forma híbrida:
* **Google Gemini API (Recomendado):** Totalmente gratuita en [Google AI Studio](https://aistudio.google.com/app/apikey). Proporciona búsqueda web y razonamiento inmediato.
* **Pexels API:** Gratuita en [Pexels API](https://www.pexels.com/api/). Permite buscar miles de vídeos 4K y 1080p sin coste.
* **Pixabay API:** Gratuita en [Pixabay API](https://pixabay.com/api/docs/). Amplia biblioteca de vídeos tecnológicos.

Todas las claves se configuran una única vez en la pestaña **Ajustes** y se guardan localmente en `config.json`.

