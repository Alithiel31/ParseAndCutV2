document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('audioFile');
    const dropZone = document.getElementById('dropZone'); // Ajouté pour le drag & drop
    const fileName = document.getElementById('fileName');
    const submitBtn = document.getElementById('submitBtn');
    const loader = document.getElementById('loader');
    const resultArea = document.getElementById('resultArea');
    const output = document.getElementById('output');
    const copyBtn = document.getElementById('copyBtn');

    // 1. GESTION DU DRAG & DROP
    ['dragover', 'dragleave', 'drop'].forEach(name => {
        dropZone.addEventListener(name, e => {
            e.preventDefault();
            e.stopPropagation();
        });
    });

    dropZone.addEventListener('drop', e => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files; // On injecte le fichier glissé dans l'input
            fileName.textContent = `Fichier prêt : ${files[0].name}`;
            console.log("Fichier reçu via Drop:", files[0].name);
        }
    });

    // 2. AFFICHAGE NOM (CLIC CLASSIQUE)
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            fileName.textContent = `Fichier prêt : ${fileInput.files[0].name}`;
            console.log("Fichier sélectionné via clic:", fileInput.files[0].name);
        }
    });

    // 3. ENVOI AU SERVEUR
    submitBtn.addEventListener('click', async () => {
        if (fileInput.files.length === 0) {
            alert("Sélectionnez d'abord un fichier audio.");
            return;
        }

        console.log("Début de l'envoi vers Railway...");
        const formData = new FormData();
        formData.append('audio', fileInput.files[0]);

        // Interface
        submitBtn.disabled = true;
        loader.classList.remove('hidden');
        resultArea.classList.add('hidden');

        try {
            const response = await fetch('/process', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                // Si Railway renvoie une erreur 413, c'est que le fichier est trop gros
                if (response.status === 413) throw new Error("Fichier trop volumineux pour le serveur.");
                const errorData = await response.json();
                throw new Error(errorData.error || "Erreur serveur inconnue");
            }

            const data = await response.json();

            if (data.markdown) {
                output.innerHTML = marked.parse(data.markdown);
                resultArea.classList.remove('hidden');
                console.log("Transcription réussie !");
            }
        } catch (error) {
            console.error("Erreur Fetch:", error);
            alert("Erreur : " + error.message);
        } finally {
            loader.classList.add('hidden');
            submitBtn.disabled = false;
        }
    });

    // 4. COPIE
    copyBtn.addEventListener('click', () => {
        const textToCopy = output.innerText;
        navigator.clipboard.writeText(textToCopy).then(() => {
            const originalText = copyBtn.textContent;
            copyBtn.textContent = "Copié ! ✅";
            setTimeout(() => copyBtn.textContent = originalText, 2000);
        });
    });
});