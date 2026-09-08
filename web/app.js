// Estado global de la aplicación
const state = {
    activeTab: 'tab-script',
    selectedFormat: 'short',
    selectedDuration: 60,
    currentProject: null,
    currentScriptText: '',
    selectedBrollClips: [],
    searchResults: [],
    config: {},
};

// === ESCALADO Y ZOOM DE INTERFAZ ===
function applyZoom(val, saveServer = false) {
    const scale = Math.round(parseFloat(val) * 100) / 100;
    const pct = Math.round(scale * 100);
    document.documentElement.style.zoom = scale;
    localStorage.setItem('capa_cero_zoom', scale.toFixed(2));

    const selector = document.getElementById('zoom-selector');
    if (selector) {
        let found = false;
        for (let opt of selector.options) {
            if (Math.abs(parseFloat(opt.value) - scale) < 0.01) {
                selector.value = opt.value;
                found = true;
                break;
            }
        }
        if (!found) {
            let customOpt = selector.querySelector('option[data-custom="true"]');
            if (!customOpt) {
                customOpt = document.createElement('option');
                customOpt.setAttribute('data-custom', 'true');
                customOpt.className = 'bg-gray-900 text-gray-100';
                customOpt.style.backgroundColor = '#111827';
                customOpt.style.color = '#F3F4F6';
                selector.appendChild(customOpt);
            }
            customOpt.value = scale.toFixed(2);
            customOpt.text = `Zoom ${pct}%`;
            selector.value = scale.toFixed(2);
        }
    }

    if (saveServer) {
        // Persistir zoom en config.json
        fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ui_zoom: `${pct}%` })
        }).catch(() => {});
    }
}

function adjustZoom(delta) {
    let current = parseFloat(localStorage.getItem('capa_cero_zoom') || '1.15');
    current = Math.min(Math.max(current + delta, 0.85), 1.60);
    const rounded = Math.round(current * 100) / 100;
    applyZoom(rounded, true);
}

function changeZoomSelect(val) {
    applyZoom(val, true);
}

// Inicialización al cargar la página
document.addEventListener('DOMContentLoaded', async () => {
    // Restaurar zoom preferido (por defecto 115% para nitidez en 2K/4K)
    const savedZoom = localStorage.getItem('capa_cero_zoom') || '1.15';
    applyZoom(savedZoom, false);

    // Limpiar cualquier residuo de autofill de credenciales en notas tecnicas
    const cleanAutofill = () => {
        const ctxInput = document.getElementById('script-context');
        if (ctxInput && (ctxInput.value === 'aalcaide45' || ctxInput.value.toLowerCase().includes('aalcaide'))) {
            ctxInput.value = '';
        }
    };
    cleanAutofill();
    setTimeout(cleanAutofill, 250);
    setTimeout(cleanAutofill, 800);

    // Listener para buscar B-Roll pulsando Enter en el input
    const brollInput = document.getElementById('broll-search-input');
    if (brollInput) {
        brollInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchBroll();
            }
        });
    }

    await loadSettings();
    await loadProjectsList();
    await loadModelsStatus();
});

// === GESTIÓN DE PESTAÑAS ===
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(el => {
        el.classList.remove('active');
        el.classList.add('text-gray-400');
    });

    const target = document.getElementById(tabId);
    if (target) target.classList.remove('hidden');

    const activeBtn = document.getElementById(`btn-${tabId}`);
    if (activeBtn) {
        activeBtn.classList.add('active');
        activeBtn.classList.remove('text-gray-400');
    }

    state.activeTab = tabId;

    if (tabId === 'tab-projects') loadProjectsList();
    if (tabId === 'tab-models') loadModelsStatus();
}

// === SELECTOR DE FORMATO ===
function selectFormat(type, durationSec) {
    state.selectedFormat = type;
    state.selectedDuration = durationSec;

    document.querySelectorAll('.format-btn').forEach(btn => {
        btn.classList.remove('border-blue-500', 'bg-blue-600/20', 'text-blue-300');
        btn.classList.add('border-gray-700', 'bg-gray-800/80', 'text-gray-200');
    });

    event.currentTarget.classList.remove('border-gray-700', 'bg-gray-800/80', 'text-gray-200');
    event.currentTarget.classList.add('border-blue-500', 'bg-blue-600/20', 'text-blue-300');
}

// === GENERACIÓN DE GUION ===
async function generateScript() {
    const topic = document.getElementById('script-topic').value.trim();
    if (!topic) {
        showToast('Por favor, escribe un tema para el vídeo.', 'warning');
        return;
    }

    const context = document.getElementById('script-context').value.trim();
    const loader = document.getElementById('script-loader');
    const resultArea = document.getElementById('script-result');
    const brollContainer = document.getElementById('broll-tags-container');

    loader.classList.remove('hidden');

    // Sincronizar el tema con la pestaña viral
    document.getElementById('viral-topic-input').value = topic;
    document.getElementById('broll-search-input').value = topic;

    try {
        const resp = await fetch('/api/script/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic: topic,
                content_type: state.selectedFormat,
                duration_sec: state.selectedDuration,
                context: context,
            })
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Error al generar el guion');
        }

        const data = await resp.json();
        state.currentScriptText = data.script;
        resultArea.value = data.script;

        // Actualizar contador
        document.getElementById('script-stats').innerText = `${data.word_count} palabras (~${data.estimated_duration_sec} seg)`;

        // Renderizar tags de B-roll sugeridos
        brollContainer.innerHTML = '';
        if (data.broll_suggestions && data.broll_suggestions.length > 0) {
            data.broll_suggestions.forEach(tag => {
                const badge = document.createElement('button');
                badge.className = 'px-2.5 py-1 rounded-lg bg-blue-950/60 hover:bg-blue-900 border border-blue-800/60 text-blue-300 text-xs font-medium transition-all flex items-center gap-1.5';
                badge.innerHTML = `<i class="fa-solid fa-magnifying-glass text-[10px]"></i> ${tag}`;
                badge.onclick = () => {
                    document.getElementById('broll-search-input').value = tag;
                    switchTab('tab-broll');
                    searchBroll();
                };
                brollContainer.appendChild(badge);
            });
        }

        showToast('¡Guion generado y contrastado con éxito!', 'success');
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        loader.classList.add('hidden');
    }
}

// === BÚSQUEDA Y GESTIÓN DE B-ROLL ===
async function searchBroll() {
    const query = document.getElementById('broll-search-input').value.trim();
    if (!query) {
        showToast('Escribe un término de búsqueda para B-roll.', 'warning');
        return;
    }

    const gallery = document.getElementById('broll-gallery');
    gallery.innerHTML = `
        <div class="col-span-full py-16 text-center text-blue-400 space-y-3">
            <div class="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p class="text-sm font-medium">Buscando masivamente en español e inglés en Pexels y Pixabay...</p>
        </div>
    `;

    try {
        // Buscar masivamente (hasta 80 clips en español e inglés combinados)
        const resp = await fetch('/api/broll/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, limit: 80 })
        });

        const data = await resp.json();
        state.searchResults = data.results || [];
        renderBrollGallery(state.searchResults);
        showToast(`Se han encontrado ${state.searchResults.length} clips para tu contenido.`, 'info');
    } catch (e) {
        gallery.innerHTML = `<div class="col-span-full py-10 text-center text-rose-400">Error buscando B-Roll: ${e.message}</div>`;
    }
}

function renderBrollGallery(clips) {
    const gallery = document.getElementById('broll-gallery');
    gallery.innerHTML = '';

    if (!clips || clips.length === 0) {
        gallery.innerHTML = `
            <div class="col-span-full py-16 text-center text-gray-500 space-y-2">
                <i class="fa-solid fa-triangle-exclamation text-3xl text-amber-500"></i>
                <p class="text-sm">No se encontraron clips para este término. Prueba en inglés o términos más generales (ej: "3D printing timelapse").</p>
            </div>
        `;
        return;
    }

    clips.forEach(clip => {
        const isSelected = state.selectedBrollClips.some(c => c.id === clip.id);
        const card = document.createElement('div');
        // Permitir clic en cualquier parte de la tarjeta para seleccionar
        card.className = `video-card cursor-pointer relative bg-gray-900 border ${isSelected ? 'border-blue-500 ring-2 ring-blue-500/50 bg-blue-950/20' : 'border-gray-800 hover:border-gray-700'} rounded-xl overflow-hidden shadow-lg flex flex-col transition-all select-none`;

        card.innerHTML = `
            <div class="relative aspect-video bg-black overflow-hidden group">
                <img src="${clip.thumbnail}" alt="${clip.title}" class="w-full h-full object-cover transition-opacity duration-300 group-hover:opacity-0">
                <video src="${clip.preview_url}" loop muted playsinline preload="none" class="absolute inset-0 w-full h-full object-cover opacity-0 group-hover:opacity-100 transition-opacity duration-300"></video>
                
                <div class="absolute top-2 left-2 flex gap-1 z-10 pointer-events-none">
                    <span class="px-2 py-0.5 rounded bg-black/70 backdrop-blur-md text-[10px] font-bold text-blue-400 border border-white/10">${clip.quality || '1080p'}</span>
                    <span class="px-2 py-0.5 rounded bg-black/70 backdrop-blur-md text-[10px] font-medium text-gray-300 border border-white/10">${clip.source}</span>
                </div>

                <div class="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/70 backdrop-blur-md text-[10px] font-mono text-gray-300 pointer-events-none">
                    ${clip.duration}s
                </div>
            </div>

            <div class="p-3 flex items-center justify-between gap-3 flex-1">
                <div class="truncate text-xs font-medium ${isSelected ? 'text-blue-200 font-semibold' : 'text-gray-300'}" title="${clip.title}">
                    ${clip.title}
                </div>

                <!-- Tick / Checkmark de Selección en la Esquina Inferior Derecha -->
                <div class="flex-shrink-0 flex items-center justify-center">
                    <div class="w-6 h-6 rounded-lg flex items-center justify-center border transition-all ${isSelected ? 'bg-blue-600 border-blue-400 text-white shadow-md shadow-blue-500/30' : 'bg-gray-800/80 border-gray-700 text-transparent hover:border-gray-500'}">
                        <i class="fa-solid fa-check text-xs"></i>
                    </div>
                </div>
            </div>
        `;

        // Reproducir preview al dejar el ratón encima (hover) sin alterar la selección
        const videoEl = card.querySelector('video');
        card.addEventListener('mouseenter', () => {
            if (videoEl && videoEl.paused) videoEl.play().catch(() => {});
        });
        card.addEventListener('mouseleave', () => {
            if (videoEl && !videoEl.paused) {
                videoEl.pause();
                videoEl.currentTime = 0;
            }
        });

        // Clic en cualquier parte de la tarjeta para alternar la selección
        card.addEventListener('click', (e) => {
            toggleClipSelection(clip.id);
        });

        gallery.appendChild(card);
    });

    updateSelectionBar();
}

function toggleClipSelection(clipId) {
    const clip = state.searchResults.find(c => c.id === clipId);
    if (!clip) return;

    const idx = state.selectedBrollClips.findIndex(c => c.id === clipId);
    if (idx >= 0) {
        state.selectedBrollClips.splice(idx, 1);
    } else {
        state.selectedBrollClips.push(clip);
    }

    renderBrollGallery(state.searchResults);
}

function updateSelectionBar() {
    const bar = document.getElementById('selection-bar');
    const countText = document.getElementById('selected-count-text');
    const count = state.selectedBrollClips.length;

    if (count > 0) {
        bar.classList.remove('hidden');
        countText.innerText = `${count} clip${count > 1 ? 's' : ''} seleccionado${count > 1 ? 's' : ''}`;
    } else {
        bar.classList.add('hidden');
    }
}

function clearSelectedClips() {
    state.selectedBrollClips = [];
    renderBrollGallery(state.searchResults);
}

async function downloadSelectedClips() {
    if (state.selectedBrollClips.length === 0) return;

    // Asegurar proyecto
    await ensureActiveProject();

    showToast(`Descargando ${state.selectedBrollClips.length} clips completos en MP4...`, 'info');

    try {
        const resp = await fetch('/api/broll/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_path: state.currentProject.project_path,
                clips: state.selectedBrollClips,
            })
        });

        const data = await resp.json();
        showToast(`¡${data.downloaded_count} clips descargados con éxito en la carpeta de DaVinci!`, 'success');
        clearSelectedClips();
        loadProjectsList();
    } catch (e) {
        showToast(`Error al descargar: ${e.message}`, 'error');
    }
}

async function autoDownloadBest() {
    const query = document.getElementById('broll-search-input').value.trim();
    if (!query) {
        showToast('Escribe un tema para la auto-descarga.', 'warning');
        return;
    }

    await ensureActiveProject();
    showToast('Buscando y descargando automáticamente los mejores 6 clips...', 'info');

    try {
        const resp = await fetch('/api/broll/download-best', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_path: state.currentProject.project_path,
                query: query,
                count: 6,
            })
        });

        const data = await resp.json();
        showToast(`¡${data.downloaded_count} clips descargados automáticamente!`, 'success');
        loadProjectsList();
    } catch (e) {
        showToast(`Error en descarga automática: ${e.message}`, 'error');
    }
}

// === SUITE VIRAL (TÍTULOS, MINIATURAS, SEO) ===
async function generateViralTitles() {
    const topic = document.getElementById('viral-topic-input').value.trim() || document.getElementById('script-topic').value.trim();
    if (!topic) {
        showToast('Escribe un tema para generar títulos.', 'warning');
        return;
    }

    const container = document.getElementById('titles-container');
    container.innerHTML = '<div class="text-blue-400 p-4 text-center"><i class="fa-solid fa-spinner animate-spin"></i> Generando 12 títulos de alto CTR...</div>';

    try {
        const resp = await fetch('/api/titles/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: topic })
        });
        const data = await resp.json();
        container.innerHTML = `<pre class="whitespace-pre-wrap leading-relaxed text-xs text-gray-200">${data.raw_titles}</pre>`;
    } catch (e) {
        container.innerHTML = `<div class="text-rose-400 p-3">Error: ${e.message}</div>`;
    }
}

async function generateViralThumbnails() {
    const topic = document.getElementById('viral-topic-input').value.trim() || document.getElementById('script-topic').value.trim();
    if (!topic) {
        showToast('Escribe un tema para las miniaturas.', 'warning');
        return;
    }

    const container = document.getElementById('thumbnails-container');
    container.innerHTML = '<div class="text-indigo-400 p-4 text-center"><i class="fa-solid fa-spinner animate-spin"></i> Generando propuestas de miniatura para ChatGPT...</div>';

    try {
        const resp = await fetch('/api/thumbnails/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: topic })
        });
        const data = await resp.json();
        container.innerHTML = `<pre class="whitespace-pre-wrap leading-relaxed text-xs text-gray-200">${data.thumbnail_proposals}</pre>`;
    } catch (e) {
        container.innerHTML = `<div class="text-rose-400 p-3">Error: ${e.message}</div>`;
    }
}

async function generateViralSeo() {
    const topic = document.getElementById('viral-topic-input').value.trim() || document.getElementById('script-topic').value.trim();
    if (!topic) {
        showToast('Escribe un tema para la caja SEO.', 'warning');
        return;
    }

    const seoArea = document.getElementById('seo-result');
    seoArea.value = 'Generando descripción con tu plantilla fija, timestamps y tags...';

    try {
        const resp = await fetch('/api/seo/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic: topic,
                script_summary: state.currentScriptText ? state.currentScriptText.substring(0, 300) : topic
            })
        });
        const data = await resp.json();
        seoArea.value = data.seo_package;
        showToast('¡Paquete SEO armado correctamente!', 'success');
    } catch (e) {
        seoArea.value = `Error: ${e.message}`;
    }
}

// === GESTIÓN DE PROYECTOS PARA DAVINCI ===
async function ensureActiveProject() {
    if (!state.currentProject) {
        const topic = document.getElementById('script-topic').value.trim() || 'Proyecto_Nuevo';
        await createCurrentProjectBundle(topic);
    }
}

async function createCurrentProjectBundle(forcedTopic) {
    const topic = forcedTopic || document.getElementById('script-topic').value.trim() || 'Proyecto_Sin_Titulo';
    const script = document.getElementById('script-result').value;
    const titles = document.getElementById('titles-container').innerText;
    const thumbnails = document.getElementById('thumbnails-container').innerText;
    const seo = document.getElementById('seo-result').value;

    try {
        const resp = await fetch('/api/projects/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic: topic,
                script: script,
                titles: titles,
                thumbnails: thumbnails,
                seo: seo,
            })
        });

        const data = await resp.json();
        state.currentProject = data.bundle;
        showToast(`Proyecto creado: ${data.bundle.project_name}`, 'success');
        loadProjectsList();
    } catch (e) {
        showToast(`Error creando proyecto: ${e.message}`, 'error');
    }
}

async function loadProjectsList() {
    const container = document.getElementById('projects-list-container');
    try {
        const resp = await fetch('/api/projects/list');
        const list = await resp.json();

        if (!list || list.length === 0) {
            container.innerHTML = '<p class="text-xs text-gray-500 italic">Aún no has creado carpetas de proyecto.</p>';
            return;
        }

        container.innerHTML = '';
        list.forEach(p => {
            const card = document.createElement('div');
            card.className = 'p-4 rounded-xl bg-gray-950/60 border border-gray-800 flex items-center justify-between gap-4 hover:border-gray-700 transition-all';
            card.innerHTML = `
                <div>
                    <div class="font-bold text-sm text-gray-200 flex items-center gap-2">
                        <i class="fa-solid fa-folder text-amber-400"></i> ${p.name}
                    </div>
                    <div class="text-[11px] text-gray-500 mt-1 flex items-center gap-3">
                        <span><i class="fa-regular fa-clock"></i> ${p.modified}</span>
                        <span><i class="fa-solid fa-video text-blue-400"></i> ${p.broll_count} vídeos B-Roll</span>
                    </div>
                </div>
                <button onclick="openFolder('${p.path.replace(/\\/g, '\\\\')}')" class="px-3.5 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-semibold flex items-center gap-1.5 transition-all">
                    <i class="fa-solid fa-arrow-up-right-from-square text-xs"></i> Abrir en Explorer / DaVinci
                </button>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        container.innerHTML = `<p class="text-xs text-rose-400">Error: ${e.message}</p>`;
    }
}

async function openFolder(path) {
    try {
        await fetch('/api/projects/open', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: path })
        });
    } catch (e) {
        showToast('Error al abrir la carpeta en Explorer', 'error');
    }
}

// === GESTOR DE MODELOS (IAsModels) ===
async function loadModelsStatus() {
    const totalEl = document.getElementById('models-total-size');
    const tableEl = document.getElementById('models-table-container');

    try {
        const resp = await fetch('/api/models/status');
        const data = await resp.json();

        totalEl.innerText = data.total_formatted || '0.00 GB';

        tableEl.innerHTML = '';
        data.recommended.forEach(m => {
            const row = document.createElement('div');
            row.className = 'p-4 rounded-xl bg-gray-950/40 border border-gray-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3';

            let actionBtn = '';
            if (m.installed) {
                actionBtn = `
                    <div class="flex items-center gap-2">
                        <span class="px-2.5 py-1 rounded-md bg-emerald-950/60 border border-emerald-800/60 text-emerald-400 text-xs font-bold">
                            <i class="fa-solid fa-circle-check"></i> Listo (${m.installed_size})
                        </span>
                        <button onclick="deleteModel('${m.category}', '${m.filename}')" class="px-2.5 py-1 rounded bg-rose-950 hover:bg-rose-900 text-rose-300 text-xs font-medium" title="Eliminar para liberar espacio">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                `;
            } else if (m.downloading) {
                actionBtn = `
                    <span class="px-3 py-1 rounded-md bg-blue-900/40 border border-blue-700/60 text-blue-300 text-xs font-medium animate-pulse">
                        <i class="fa-solid fa-spinner animate-spin"></i> Descargando (${m.download_percent}%)...
                    </span>
                `;
            } else {
                actionBtn = `
                    <button onclick="downloadModel('${m.id}')" class="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-all flex items-center gap-1.5 shadow">
                        <i class="fa-solid fa-download"></i> Descargar (${m.size_gb} GB)
                    </button>
                `;
            }

            row.innerHTML = `
                <div>
                    <div class="font-bold text-xs text-white flex items-center gap-2">
                        ${m.name}
                        <span class="text-[10px] px-2 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">${m.category}</span>
                    </div>
                    <div class="text-[11px] text-gray-400 mt-0.5">${m.description}</div>
                </div>
                <div>${actionBtn}</div>
            `;
            tableEl.appendChild(row);
        });
    } catch (e) {
        tableEl.innerHTML = `<p class="text-xs text-rose-400">Error: ${e.message}</p>`;
    }
}

async function downloadModel(modelId) {
    try {
        await fetch('/api/models/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_id: modelId })
        });
        showToast('Descarga iniciada en segundo plano dentro de IAsModels.', 'info');
        loadModelsStatus();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function deleteModel(category, filename) {
    if (!confirm(`¿Deseas eliminar ${filename} para liberar espacio en disco?`)) return;
    try {
        await fetch('/api/models/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category: category, filename: filename })
        });
        showToast('Modelo eliminado del disco.', 'success');
        loadModelsStatus();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function purgeModelsCategory(category) {
    if (!confirm(`¿Estás seguro de que quieres eliminar todos los modelos de ${category} para liberar espacio?`)) return;
    try {
        const resp = await fetch('/api/models/purge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category: category })
        });
        const data = await resp.json();
        showToast(`Se han eliminado ${data.purged_count} archivos de ${category}.`, 'success');
        loadModelsStatus();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// === AJUSTES Y CONFIGURACIÓN PERSISTENTE ===
async function loadSettings() {
    try {
        const resp = await fetch('/api/config');
        const cfg = await resp.json();
        state.config = cfg;

        // Sincronizar zoom si viene en la configuracion
        if (cfg.ui_zoom && !localStorage.getItem('capa_cero_zoom')) {
            const parsedZoom = parseFloat(cfg.ui_zoom) / 100;
            if (!isNaN(parsedZoom) && parsedZoom > 0.5) applyZoom(parsedZoom, false);
        }

        document.getElementById('cfg-download-path').value = cfg.download_path || '';
        
        // Cargar claves de Gemini (filtrando contraseñas accidentales)
        let keysList = cfg.gemini_api_keys && cfg.gemini_api_keys.length > 0
            ? cfg.gemini_api_keys.join('\n')
            : (cfg.gemini_api_key || '');
        if (keysList.includes('Seatleon')) keysList = '';
        document.getElementById('cfg-gemini-key').value = keysList;

        if (document.getElementById('cfg-gemini-model')) {
            document.getElementById('cfg-gemini-model').value = cfg.gemini_model || 'gemini-2.0-flash';
        }

        let pexelsKey = cfg.pexels_api_key || '';
        if (pexelsKey.includes('Seatleon')) pexelsKey = '';
        document.getElementById('cfg-pexels-key').value = pexelsKey;

        document.getElementById('cfg-pixabay-key').value = cfg.pixabay_api_key || '';
        document.getElementById('cfg-ai-provider').value = cfg.ai_provider || 'gemini';
        document.getElementById('cfg-youtube-template').value = cfg.youtube_fixed_template || '';

        // Actualizar badge en topbar
        const badge = document.getElementById('ai-mode-badge');
        if (cfg.ai_provider === 'local') {
            badge.className = 'px-2.5 py-1 rounded-md bg-emerald-900/30 border border-emerald-700/40 text-emerald-400 text-xs font-semibold flex items-center gap-1.5';
            badge.innerHTML = '<i class="fa-solid fa-microchip text-xs"></i> <span>RTX 4090 Local</span>';
        } else {
            const mName = cfg.gemini_model ? cfg.gemini_model.replace('gemini-', '').toUpperCase() : '2.0 FLASH';
            badge.className = 'px-2.5 py-1 rounded-md bg-blue-900/30 border border-blue-700/40 text-blue-400 text-xs font-semibold flex items-center gap-1.5';
            badge.innerHTML = `<i class="fa-solid fa-cloud text-xs"></i> <span>Gemini ${mName}</span>`;
        }
    } catch (e) {
        console.error('Error cargando configuración:', e);
    }
}

async function saveSettings() {
    const rawKeys = document.getElementById('cfg-gemini-key').value;
    const parsedKeys = rawKeys.split(/[\n,]+/).map(k => k.trim()).filter(k => k.length > 0);

    const newCfg = {
        download_path: document.getElementById('cfg-download-path').value.trim(),
        gemini_api_key: parsedKeys.length > 0 ? parsedKeys[0] : '',
        gemini_api_keys: parsedKeys,
        gemini_model: document.getElementById('cfg-gemini-model') ? document.getElementById('cfg-gemini-model').value : 'gemini-2.0-flash',
        pexels_api_key: document.getElementById('cfg-pexels-key').value.trim(),
        pixabay_api_key: document.getElementById('cfg-pixabay-key').value.trim(),
        ai_provider: document.getElementById('cfg-ai-provider').value,
        youtube_fixed_template: document.getElementById('cfg-youtube-template').value,
    };

    try {
        const resp = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newCfg)
        });
        const data = await resp.json();
        state.config = data.config;
        showToast('Ajustes guardados permanentemente (Rotación de claves activa).', 'success');
        loadSettings();
    } catch (e) {
        showToast(`Error al guardar: ${e.message}`, 'error');
    }
}

// === UTILIDADES (COPIAR TEXTO Y TOAST) ===
function copyScriptText() {
    const text = document.getElementById('script-result').value;
    if (!text) return;
    navigator.clipboard.writeText(text);
    showToast('Guion copiado al portapapeles.', 'info');
}

function copySeoText() {
    const text = document.getElementById('seo-result').value;
    if (!text) return;
    navigator.clipboard.writeText(text);
    showToast('Paquete SEO copiado al portapapeles.', 'info');
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const msg = document.getElementById('toast-msg');
    const icon = document.getElementById('toast-icon');

    msg.innerText = message;

    if (type === 'success') {
        icon.className = 'fa-solid fa-circle-check text-emerald-400 text-base';
    } else if (type === 'error') {
        icon.className = 'fa-solid fa-circle-xmark text-rose-400 text-base';
    } else if (type === 'warning') {
        icon.className = 'fa-solid fa-triangle-exclamation text-amber-400 text-base';
    } else {
        icon.className = 'fa-solid fa-circle-info text-blue-400 text-base';
    }

    toast.classList.remove('translate-y-20', 'opacity-0');
    setTimeout(() => {
        toast.classList.add('translate-y-20', 'opacity-0');
    }, 4000);
}

