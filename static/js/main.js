document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('audioFile');
    const fileName = document.getElementById('fileName');
    const submitBtn = document.getElementById('submitBtn');
    const loader = document.getElementById('loader');
    const resultArea = document.getElementById('resultArea');
    const output = document.getElementById('output');
    const copyBtn = document.getElementById('copyBtn');

    // Afficher le nom du fichier sélectionné
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            fileName.textContent = `Fichier prêt : ${fileInput.files[0].name}`;
        }
    });

    // Envoyer le fichier au serveur
    submitBtn.addEventListener('click', async () => {
        if (fileInput.files.length === 0) {
            alert("Sélectionnez d'abord un fichier audio.");
            return;
        }

        const formData = new FormData();
        formData.append('audio', fileInput.files[0]);

        // Mise à jour de l'interface
        submitBtn.disabled = true;
        loader.classList.remove('hidden');
        resultArea.classList.add('hidden');

        try {
            const response = await fetch('/process', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.markdown) {
                // Utilisation de Marked.js pour transformer le Markdown en HTML propre
                output.innerHTML = marked.parse(data.markdown);
                resultArea.classList.remove('hidden');
            } else {
                alert("Erreur serveur : " + data.error);
            }
        } catch (error) {
            console.error(error);
            alert("Erreur lors de la communication avec le Raspberry Pi.");
        } finally {
            loader.classList.add('hidden');
            submitBtn.disabled = false;
        }
    });

    // Copier dans le presse-papier
    copyBtn.addEventListener('click', () => {
        const textToCopy = output.innerText;
        navigator.clipboard.writeText(textToCopy).then(() => {
            const originalText = copyBtn.textContent;
            copyBtn.textContent = "Copié ! ✅";
            setTimeout(() => copyBtn.textContent = originalText, 2000);
        });
    });
});