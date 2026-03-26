document.addEventListener('DOMContentLoaded', () => {
    const fileInput   = document.getElementById('audioFile');
    const dropZone    = document.getElementById('dropZone');
    const fileName    = document.getElementById('fileName');
    const submitBtn   = document.getElementById('submitBtn');
    const loader      = document.getElementById('loader');
    const statusText  = document.getElementById('statusText');
    const resultArea  = document.getElementById('resultArea');
    const output      = document.getElementById('output');
    const copyBtn     = document.getElementById('copyBtn');
    const statsBar    = document.getElementById('statsBar');
    const errorBanner = document.getElementById('errorBanner');

    const MAX_SIZE_MB = 100;

    // Étapes affichées pendant le traitement
    const STEPS = [
        { id: 'step-upload',  label: '📤 Envoi'        },
        { id: 'step-cut',     label: '✂️ Découpage'     },
        { id: 'step-whisper', label: '🎙️ Transcription' },
        { id: 'step-llm',     label: '🧠 Structuration' },
    ];

    // Injection des badges dans le loader
    const progressEl = document.getElementById('progressSteps');
    STEPS.forEach(s => {
        const span = document.createElement('span');
        span.className = 'step-badge';
        span.id = s.id;
        span.textContent = s.label;
        progressEl.appendChild(span);
    });

    function setStep(activeId) {
        STEPS.forEach(s => {
            const el = document.getElementById(s.id);
            el.classList.remove('active', 'done');
            const idx = STEPS.findIndex(x => x.id === s.id);
            const activeIdx = STEPS.findIndex(x => x.id === activeId);
            if (idx < activeIdx) el.classList.add('done');
            else if (idx === activeIdx) el.classList.add('active');
        });
    }

    function showError(msg) {
        errorBanner.textContent = '⚠️ ' + msg;
        errorBanner.classList.remove('hidden');
    }

    function clearError() {
        errorBanner.classList.add('hidden');
        errorBanner.textContent = '';
    }

    function setFile(file) {
        if (!file) return;
        if (file.size > MAX_SIZE_MB * 1024 * 1024) {
            showError(`Fichier trop volumineux (max ${MAX_SIZE_MB} Mo).`);
            return;
        }
        clearError();
        fileName.textContent = `📎 ${file.name} — ${(file.size / 1024 / 1024).toFixed(1)} Mo`;
    }

    // --- Drag & drop ---
    dropZone.addEventListener('dragover', e => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            setFile(files[0]);
        }
    });

    // --- Sélection classique ---
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) setFile(fileInput.files[0]);
    });

    // --- Envoi ---
    submitBtn.addEventListener('click', async () => {
        if (fileInput.files.length === 0) {
            showError('Sélectionnez d\'abord un fichier audio.');
            return;
        }
        clearError();
        resultArea.classList.add('hidden');
        statsBar.classList.add('hidden');

        const formData = new FormData();
        formData.append('audio', fileInput.files[0]);

        submitBtn.disabled = true;
        loader.classList.remove('hidden');
        setStep('step-upload');
        statusText.textContent = 'Envoi du fichier…';

        // Simule la progression (le serveur ne streame pas encore)
        const stepTimings = [
            { id: 'step-cut',     delay: 1500, label: 'Découpage en cours…'       },
            { id: 'step-whisper', delay: 4000, label: 'Transcription Whisper…'     },
            { id: 'step-llm',     delay: 9000, label: 'Structuration avec Llama…'  },
        ];
        const timers = stepTimings.map(({ id, delay, label }) =>
            setTimeout(() => { setStep(id); statusText.textContent = label; }, delay)
        );

        try {
            const response = await fetch('/process', { method: 'POST', body: formData });
            timers.forEach(clearTimeout);

            if (!response.ok) {
                const err = await response.json().catch(() => ({ error: `Erreur HTTP ${response.status}` }));
                throw new Error(err.error || `Erreur ${response.status}`);
            }

            const data = await response.json();

            if (data.markdown) {
                // Stats
                if (data.stats) {
                    statsBar.innerHTML = `
                        <span>🔀 ${data.stats.chunks} chunk(s)</span>
                        <span>📝 ${data.stats.transcription_chars.toLocaleString()} caractères transcrits</span>
                    `;
                    statsBar.classList.remove('hidden');
                }

                output.innerHTML = marked.parse(data.markdown);
                resultArea.classList.remove('hidden');

                // Marque toutes les étapes comme terminées
                STEPS.forEach(s => {
                    const el = document.getElementById(s.id);
                    el.classList.remove('active');
                    el.classList.add('done');
                });
                statusText.textContent = '✅ Fiche générée !';
                setTimeout(() => resultArea.scrollIntoView({ behavior: 'smooth', block: 'start' }), 200);
            }

        } catch (error) {
            timers.forEach(clearTimeout);
            showError(error.message);
        } finally {
            setTimeout(() => loader.classList.add('hidden'), 800);
            submitBtn.disabled = false;
        }
    });

    // --- Copie ---
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(output.innerText).then(() => {
            const orig = copyBtn.textContent;
            copyBtn.textContent = '✅ Copié !';
            setTimeout(() => copyBtn.textContent = orig, 2000);
        });
    });
});