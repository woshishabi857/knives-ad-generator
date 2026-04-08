/**
 * KnifeAd Pro — Batch Mode Frontend Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM refs
    const knifeUploadZone = document.getElementById('knife-upload-zone');
    const knifeInput = document.getElementById('knife-input');
    const knifePreviews = document.getElementById('knife-previews');
    const knifePlaceholder = document.getElementById('knife-placeholder');

    const presetsChips = document.getElementById('presets-chips');
    const sceneList = document.getElementById('scene-list');
    const addSceneBtn = document.getElementById('add-scene-btn');

    const generateSummary = document.getElementById('generate-summary');
    const generateBtn = document.getElementById('generate-btn');
    const progressSection = document.getElementById('progress-section');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    const resultsSection = document.getElementById('results-section');
    const resultsGrid = document.getElementById('results-grid');
    const errorsList = document.getElementById('errors-list');
    const downloadAllBtn = document.getElementById('download-all-btn');

    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');
    const loadingProgress = document.getElementById('loading-progress');
    const cancelBtn = document.getElementById('cancel-btn');
    const toastContainer = document.getElementById('toast-container');

    // 当前任务 ID
    let currentTaskId = null;

    // Category Manager refs
    const categoryManagerTags = document.getElementById('category-manager-tags');
    const newCategoryNameInput = document.getElementById('new-category-name');
    const categoryAddBtn = document.getElementById('category-add-btn');

    // State
    let knifeFiles = [];       // [{file, dataUrl, category, composition}]
    let sceneCards = [];        // [{id, type, presetKey?, bgFile?, bgDataUrl?, prompt, name, selectedCategories, enabled, comboMode}]
    let presetsData = [];       // from API
    let allResults = [];        // [{label, image}]
    let sceneIdCounter = 0;

    // Categories Logic
    const DEFAULT_CATEGORIES = [
        { key: 'general', name: '通用' },
        { key: 'meat_cleaver', name: '切肉刀' },
        { key: 'veg_knife', name: '蔬菜刀' },
        { key: 'fruit_knife', name: '水果刀' },
        { key: 'packaging', name: '包装盒' },
        { key: 'combo_set', name: '组合套装' },
        { key: 'forest', name: '户外刀' }
    ];

    let categories = loadCategories();

    function loadCategories() {
        const saved = localStorage.getItem('knife_categories');
        if (saved) {
            try { return JSON.parse(saved); } catch (e) { return DEFAULT_CATEGORIES; }
        }
        return DEFAULT_CATEGORIES;
    }

    function saveCategories() {
        localStorage.setItem('knife_categories', JSON.stringify(categories));
    }

    function renderCategoryManager() {
        categoryManagerTags.innerHTML = '';
        categories.forEach(cat => {
            const tag = document.createElement('div');
            tag.className = 'category-manager-tag';
            tag.innerHTML = `
                <span>${escapeHtml(cat.name)}</span>
                ${cat.key !== 'general' ? `<span class="remove-cat" data-key="${cat.key}">✕</span>` : ''}
            `;
            const removeBtn = tag.querySelector('.remove-cat');
            if (removeBtn) {
                removeBtn.addEventListener('click', () => removeCategory(cat.key));
            }
            categoryManagerTags.appendChild(tag);
        });
    }

    function addCategory(name) {
        name = name.trim();
        if (!name) return;
        const key = 'custom_' + Date.now();
        categories.push({ key, name });
        saveCategories();
        renderCategoryManager();
        renderKnifePreviews();
        renderScenes();
        updateSummary();
    }

    function removeCategory(key) {
        if (key === 'general') return;
        categories = categories.filter(c => c.key !== key);
        // Clean up usages
        knifeFiles.forEach(k => { if (k.category === key) k.category = 'general'; });
        sceneCards.forEach(s => { s.selectedCategories = s.selectedCategories.filter(c => c !== key); });

        saveCategories();
        renderCategoryManager();
        renderKnifePreviews();
        renderScenes();
        updateSummary();
    }

    categoryAddBtn.addEventListener('click', () => {
        addCategory(newCategoryNameInput.value);
        newCategoryNameInput.value = '';
    });

    newCategoryNameInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            addCategory(newCategoryNameInput.value);
            newCategoryNameInput.value = '';
        }
    });

    // ==================== Knife Upload ====================

    knifeUploadZone.addEventListener('click', () => knifeInput.click());

    knifeInput.addEventListener('change', (e) => {
        addKnifeFiles(Array.from(e.target.files));
        knifeInput.value = '';
    });

    knifeUploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        knifeUploadZone.classList.add('dragover');
    });
    knifeUploadZone.addEventListener('dragleave', () => knifeUploadZone.classList.remove('dragover'));
    knifeUploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        knifeUploadZone.classList.remove('dragover');
        addKnifeFiles(Array.from(e.dataTransfer.files));
    });

    function addKnifeFiles(files) {
        files.forEach(file => {
            if (!file.type.startsWith('image/')) return;
            const reader = new FileReader();
            reader.onload = (ev) => {
                knifeFiles.push({ file, dataUrl: ev.target.result, category: 'general', composition: '' });
                saveSavedKnives();
                renderKnifePreviews();
                updateSummary();
            };
            reader.readAsDataURL(file);
        });
    }

    function renderKnifePreviews() {
        knifePreviews.innerHTML = '';
        if (knifeFiles.length > 0) {
            knifePlaceholder.style.display = 'none';
        } else {
            knifePlaceholder.style.display = '';
        }
        knifeFiles.forEach((item, idx) => {
            const thumb = document.createElement('div');
            thumb.className = 'knife-thumb';
            thumb.innerHTML = `
                <img src="${item.dataUrl}" alt="刀具 ${idx + 1}">
                <button class="remove-x" data-idx="${idx}">✕</button>
                <div class="knife-thumb-footer">
                    <select class="knife-category-select" data-idx="${idx}">
                        ${categories.map(c => `<option value="${c.key}" ${item.category === c.key ? 'selected' : ''}>${c.name}</option>`).join('')}
                    </select>
                    <input type="text" class="knife-composition-input" placeholder="材质 (如: 大马士革钢)" value="${escapeHtml(item.composition || '')}" data-idx="${idx}">
                </div>
            `;
            // Remove
            thumb.querySelector('.remove-x').addEventListener('click', (e) => {
                e.stopPropagation();
                knifeFiles.splice(idx, 1);
                saveSavedKnives();
                renderKnifePreviews();
                updateSummary();
            });
            // Category change
            thumb.querySelector('.knife-category-select').addEventListener('change', (e) => {
                item.category = e.target.value;
                saveSavedKnives();
                updateSummary();
            });
            // Composition change
            thumb.querySelector('.knife-composition-input').addEventListener('input', (e) => {
                item.composition = e.target.value;
                saveSavedKnives();
            });
            knifePreviews.appendChild(thumb);
        });
    }

    // ==================== Presets ====================

    async function loadPresets() {
        try {
            const res = await fetch('/api/presets');
            presetsData = await res.json();
            presetsChips.innerHTML = '';
            presetsData.forEach(p => {
                const chip = document.createElement('div');
                chip.className = 'preset-chip';
                chip.innerHTML = `
                    ${p.thumbnail ? `<img src="data:image/jpeg;base64,${p.thumbnail}">` : ''}
                    <span>${p.name}</span>
                `;
                chip.addEventListener('click', () => addPresetScene(p));
                presetsChips.appendChild(chip);
            });
        } catch (e) {
            console.error('Failed to load presets:', e);
        }
    }

    function addPresetScene(preset) {
        const id = ++sceneIdCounter;
        sceneCards.push({
            id,
            type: 'preset',
            presetKey: preset.key,
            prompt: preset.prompt,
            name: preset.name,
            selectedCategories: [preset.key], // Default to its own category
            bgDataUrl: preset.thumbnail ? `data:image/jpeg;base64,${preset.thumbnail}` : null,
            enabled: true,
            comboMode: false
        });
        renderScenes();
        updateSummary();
    }

    // ==================== Custom Scene ====================

    addSceneBtn.addEventListener('click', () => {
        const id = ++sceneIdCounter;
        sceneCards.push({
            id,
            type: 'custom',
            bgFile: null,
            bgDataUrl: null,
            prompt: '',
            name: `自定义场景 ${id}`,
            selectedCategories: [], // Default empty (means all)
            enabled: true,
            comboMode: false
        });
        renderScenes();
        updateSummary();
    });

    // ==================== Render Scenes ====================

    function renderScenes() {
        sceneList.innerHTML = '';
        sceneCards.forEach((scene, idx) => {
            const card = document.createElement('div');
            card.className = 'scene-card';
            card.dataset.id = scene.id;

            const isPreset = scene.type === 'preset';

            card.innerHTML = `
                <div class="scene-card-header">
                    <span class="scene-badge ${isPreset ? 'preset' : 'custom'}">${isPreset ? '预设' : '自定义'}</span>
                    <div class="scene-card-name">
                        <input type="text" value="${escapeHtml(scene.name)}" data-field="name">
                    </div>
                    <div class="scene-card-controls">
                        <label class="toggle-switch">
                            <input type="checkbox" data-field="enabled" ${scene.enabled ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                        </label>
                        <label class="toggle-switch">
                            <input type="checkbox" data-field="comboMode" ${scene.comboMode ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                        </label>
                        <button class="scene-remove-btn" title="删除">✕</button>
                    </div>
                </div>
                <div class="scene-card-body">
                    ${isPreset && scene.bgDataUrl
                    ? `<img class="scene-bg-preview" src="${scene.bgDataUrl}" alt="bg">`
                    : `<div class="scene-bg-upload" data-idx="${idx}">
                            ${scene.bgDataUrl
                        ? `<img src="${scene.bgDataUrl}" alt="bg">`
                        : '点击上传<br>背景图'}
                            <input type="file" accept="image/*" hidden>
                          </div>`
                }
                    <div class="scene-prompt-wrap">
                        <textarea class="scene-prompt" placeholder="输入该场景的 Prompt 描述..." data-field="prompt">${escapeHtml(scene.prompt)}</textarea>
                        <div class="scene-category-filters">
                            <div class="filter-label">目标刀具：</div>
                            ${categories.map(c => `
                                <div class="category-tag ${scene.selectedCategories.includes(c.key) ? 'active' : ''}" data-cat="${c.key}">
                                    ${c.name}
                                </div>
                            `).join('')}
                        </div>
                        <div class="scene-mode-indicators">
                            <span class="mode-indicator">
                                <strong>状态：</strong>${scene.enabled ? '启用' : '禁用'}
                            </span>
                            <span class="mode-indicator">
                                <strong>模式：</strong>${scene.comboMode ? '组合模式' : '单刀模式'}
                            </span>
                        </div>
                    </div>
                </div>
            `;

            // Remove
            card.querySelector('.scene-remove-btn').addEventListener('click', () => {
                sceneCards = sceneCards.filter(s => s.id !== scene.id);
                renderScenes();
                updateSummary();
            });

            // Name edit
            card.querySelector('input[data-field="name"]').addEventListener('input', (e) => {
                scene.name = e.target.value;
            });

            // Prompt edit
            card.querySelector('textarea[data-field="prompt"]').addEventListener('input', (e) => {
                scene.prompt = e.target.value;
                updateSummary();
            });

            // Enabled toggle
            card.querySelector('input[data-field="enabled"]').addEventListener('change', (e) => {
                scene.enabled = e.target.checked;
                renderScenes();
                updateSummary();
            });

            // Combo Mode toggle
            card.querySelector('input[data-field="comboMode"]').addEventListener('change', (e) => {
                scene.comboMode = e.target.checked;
                renderScenes();
                updateSummary();
            });

            if (!isPreset) {
                const bgUploadDiv = card.querySelector('.scene-bg-upload');
                const bgInput = bgUploadDiv.querySelector('input[type="file"]');
                bgUploadDiv.addEventListener('click', () => bgInput.click());
                bgInput.addEventListener('change', (e) => {
                    const file = e.target.files[0];
                    if (!file) return;
                    scene.bgFile = file;
                    const reader = new FileReader();
                    reader.onload = (ev) => {
                        scene.bgDataUrl = ev.target.result;
                        renderScenes();
                        updateSummary();
                    };
                    reader.readAsDataURL(file);
                });
            }

            // Category tag toggle
            card.querySelectorAll('.category-tag').forEach(tag => {
                tag.addEventListener('click', () => {
                    const cat = tag.dataset.cat;
                    if (scene.selectedCategories.includes(cat)) {
                        scene.selectedCategories = scene.selectedCategories.filter(c => c !== cat);
                    } else {
                        scene.selectedCategories.push(cat);
                    }
                    renderScenes();
                    updateSummary();
                });
            });

            sceneList.appendChild(card);
        });
    }

    // ==================== Summary & Validation ====================

    function updateSummary() {
        const knifeCount = knifeFiles.length;
        const validScenes = sceneCards.filter(s => {
            const hasPrompt = s.prompt.trim().length > 0;
            const hasBg = s.type === 'preset' ? !!s.presetKey : !!s.bgFile;
            const isEnabled = s.enabled;
            return hasPrompt && hasBg && isEnabled;
        });
        const sceneCount = validScenes.length;

        let totalTasks = 0;
        validScenes.forEach(s => {
            if (s.comboMode) {
                // 组合模式：每个场景算一个任务
                const matchedKnives = knifeFiles.filter(k => {
                    if (s.selectedCategories.length === 0) return true;
                    return s.selectedCategories.includes(k.category);
                });
                if (matchedKnives.length > 0) {
                    totalTasks += 1;
                }
            } else {
                // 单刀模式：每个刀具算一个任务
                const matchedKnives = knifeFiles.filter(k => {
                    if (s.selectedCategories.length === 0) return true;
                    return s.selectedCategories.includes(k.category);
                });
                totalTasks += matchedKnives.length;
            }
        });

        if (knifeCount === 0) {
            generateSummary.textContent = '请先上传刀具图';
            generateBtn.disabled = true;
        } else if (sceneCount === 0) {
            generateSummary.textContent = `已上传 ${knifeCount} 张刀具图 — 请添加场景任务`;
            generateBtn.disabled = true;
        } else if (totalTasks === 0) {
            generateSummary.textContent = `分类不匹配 — 没有任何刀具符合当前的场景任务`;
            generateBtn.disabled = true;
        } else {
            generateSummary.textContent = `当前任务：共 ${totalTasks} 张广告图待生成`;
            generateBtn.disabled = false;
        }
    }

    // ==================== Batch Generate ====================

    generateBtn.addEventListener('click', async () => {
        if (generateBtn.disabled) return;

        const validScenes = sceneCards.filter(s => {
            const hasPrompt = s.prompt.trim().length > 0;
            const hasBg = s.type === 'preset' ? !!s.presetKey : !!s.bgFile;
            const isEnabled = s.enabled;
            return hasPrompt && hasBg && isEnabled;
        });

        if (knifeFiles.length === 0 || validScenes.length === 0) {
            showToast('请完善刀具图和场景配置', 'error');
            return;
        }

        // Build FormData
        const formData = new FormData();

        knifeFiles.forEach(k => formData.append('knife_images', k.file));

        // Knives metadata
        const knivesMetadata = knifeFiles.map(k => ({
            category: k.category,
            composition: k.composition
        }));
        formData.append('knives_metadata', JSON.stringify(knivesMetadata));

        // Custom bg files: track index mapping
        let bgIndexMap = new Map();
        let bgIdx = 0;
        validScenes.forEach(s => {
            if (s.type === 'custom' && s.bgFile) {
                if (!bgIndexMap.has(s.id)) {
                    formData.append('bg_images', s.bgFile);
                    bgIndexMap.set(s.id, bgIdx++);
                }
            }
        });

        // Build scenes JSON
        const scenesPayload = validScenes.map(s => ({
            bg_type: s.type,
            preset_key: s.presetKey || '',
            bg_index: bgIndexMap.get(s.id) ?? -1,
            prompt: s.prompt,
            name: s.name,
            selected_categories: s.selectedCategories,
            combo_mode: s.comboMode
        }));
        formData.append('scenes', JSON.stringify(scenesPayload));

        // 清空之前的结果
        resultsSection.style.display = 'none';
        resultsGrid.innerHTML = '';
        errorsList.innerHTML = '';
        allResults = [];

        // Show loading
        loadingOverlay.classList.add('visible');
        generateBtn.disabled = true;
        progressSection.style.display = 'block';
        progressBar.style.width = '0%';
        progressText.textContent = '正在提交任务...';

        try {
            const res = await fetch('/api/batch_generate', { method: 'POST', body: formData });
            const data = await res.json();

            if (!data.success) {
                showToast(data.error || '提交失败', 'error');
                loadingOverlay.classList.remove('visible');
                generateBtn.disabled = false;
                return;
            }

            // Poll progress
            const taskId = data.task_id;
            currentTaskId = taskId; // 保存当前任务 ID
            const total = data.total;
            loadingText.textContent = `AI 正在批量生成 ${total} 张广告图...`;

            await pollProgress(taskId, total);
        } catch (e) {
            showToast(`网络错误: ${e.message}`, 'error');
            loadingOverlay.classList.remove('visible');
            generateBtn.disabled = false;
        }
    });

    async function pollProgress(taskId, total) {
        const poll = async () => {
            try {
                const res = await fetch(`/api/task_status/${taskId}`);
                const data = await res.json();

                const pct = total > 0 ? Math.round((data.completed / total) * 100) : 0;
                progressBar.style.width = pct + '%';
                progressText.textContent = `已完成 ${data.completed} / ${total}`;
                loadingProgress.textContent = `${pct}%`;

                if (data.status === 'done' || data.status === 'cancelled') {
                    loadingOverlay.classList.remove('visible');
                    generateBtn.disabled = false;
                    currentTaskId = null; // 清空当前任务 ID
                    if (data.status === 'cancelled') {
                        showToast('任务已取消', 'error');
                    } else {
                        showResults(data.results, data.errors);
                        if (data.results.length > 0) {
                            showToast(`成功生成 ${data.results.length} 张广告图！`, 'success');
                        }
                        if (data.errors.length > 0) {
                            showToast(`${data.errors.length} 张生成失败`, 'error');
                        }
                    }
                    return;
                }

                setTimeout(poll, 2000);
            } catch (e) {
                setTimeout(poll, 3000);
            }
        };
        poll();
    }

    // ==================== Results ====================

    function showResults(results, errors) {
        allResults = results;
        resultsSection.style.display = '';
        resultsGrid.innerHTML = '';
        errorsList.innerHTML = '';

        results.forEach((r, idx) => {
            const item = document.createElement('div');
            item.className = 'result-item';
            item.innerHTML = `
                <img src="data:image/png;base64,${r.image}" alt="${r.label}" data-idx="${idx}">
                <div class="result-item-footer">
                    <span class="result-item-label" title="${escapeHtml(r.label)}">${escapeHtml(r.label)}</span>
                    <button class="result-dl-btn" data-idx="${idx}">下载</button>
                </div>
            `;
            item.querySelector('img').addEventListener('click', (e) => openLightbox(e.target.src));
            item.querySelector('.result-dl-btn').addEventListener('click', () => {
                // 获取材质信息
                let composition = '';
                if (r.composition) {
                    composition = r.composition;
                } else if (r.compositions && r.compositions.length > 0) {
                    // 组合模式，使用第一个材质或所有材质的组合
                    composition = r.compositions.join('_');
                }
                downloadImage(r.image, r.label, composition);
            });
            resultsGrid.appendChild(item);
        });

        errors.forEach(err => {
            const div = document.createElement('div');
            div.className = 'error-item';
            div.textContent = '❌ ' + err;
            errorsList.appendChild(div);
        });

        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    downloadAllBtn.addEventListener('click', () => {
        allResults.forEach((r, i) => {
            // 获取材质信息
            let composition = '';
            if (r.composition) {
                composition = r.composition;
            } else if (r.compositions && r.compositions.length > 0) {
                composition = r.compositions.join('_');
            }
            setTimeout(() => downloadImage(r.image, r.label, composition), i * 300);
        });
    });

    async function downloadImage(b64, label, composition = '') {
        try {
            // 构建文件名，包含材质信息
            let filename = label.replace(/[^\w\u4e00-\u9fff.-]/g, '_');
            if (composition) {
                // 清理材质名称，使其适合作为文件名
                const cleanComposition = composition.replace(/[^\w\u4e00-\u9fff.-]/g, '_');
                filename += `_${cleanComposition}`;
            }
            filename += '.png';

            // 转换 base64 为 Blob
            const response = await fetch(`data:image/png;base64,${b64}`);
            const blob = await response.blob();

            // 使用 showSaveFilePicker API 让用户选择保存位置
            const handle = await window.showSaveFilePicker({
                suggestedName: filename,
                types: [
                    { description: 'PNG 图像', accept: { 'image/png': ['.png'] } }
                ]
            });

            // 写入文件
            const writable = await handle.createWritable();
            await writable.write(blob);
            await writable.close();
        } catch (err) {
            // 如果 API 不支持或用户取消，使用传统下载方式
            if (err.name === 'AbortError' || err.name === 'NotAllowedError') {
                // 用户取消或权限不足，使用传统方式
                const link = document.createElement('a');
                link.href = `data:image/png;base64,${b64}`;
                let filename = label.replace(/[^\w\u4e00-\u9fff.-]/g, '_');
                if (composition) {
                    const cleanComposition = composition.replace(/[^\w\u4e00-\u9fff.-]/g, '_');
                    filename += `_${cleanComposition}`;
                }
                filename += '.png';
                link.download = filename;
                link.click();
            } else {
                console.error('下载失败:', err);
                showToast('下载失败，请重试', 'error');
            }
        }
    }

    // ==================== Lightbox ====================

    let lightboxEl = null;

    function openLightbox(src) {
        if (!lightboxEl) {
            lightboxEl = document.createElement('div');
            lightboxEl.className = 'lightbox';
            lightboxEl.innerHTML = '<img>';
            lightboxEl.addEventListener('click', () => lightboxEl.classList.remove('visible'));
            document.body.appendChild(lightboxEl);
        }
        lightboxEl.querySelector('img').src = src;
        lightboxEl.classList.add('visible');
    }

    // ==================== Utils ====================

    function showToast(msg, type = 'error') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = msg;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease-out reverse forwards';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ==================== Persistence ====================

    function loadSavedKnives() {
        const saved = localStorage.getItem('knifead_saved_knives');
        if (saved) {
            try {
                const data = JSON.parse(saved);
                // Ensure dataUrl is still valid or handle it
                knifeFiles = data;
                renderKnifePreviews();
                updateSummary();
            } catch (e) {
                console.error('Failed to load saved knives:', e);
            }
        }
    }

    function saveSavedKnives() {
        // We only save the metadata and dataUrl (for simplicity in this demo)
        localStorage.setItem('knifead_saved_knives', JSON.stringify(knifeFiles));
    }

    // ==================== Cancel Button ====================
    cancelBtn.addEventListener('click', async () => {
        if (currentTaskId) {
            try {
                const res = await fetch(`/api/task_cancel/${currentTaskId}`, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    showToast('取消请求已发送', 'error');
                } else {
                    showToast(data.error || '取消失败', 'error');
                }
            } catch (e) {
                showToast(`取消失败: ${e.message}`, 'error');
            }
        } else {
            showToast('没有正在进行的任务', 'error');
        }
    });

    // ==================== Init ====================
    loadPresets();
    loadSavedKnives();
    renderCategoryManager();
    updateSummary();
});
