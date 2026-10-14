/**
 * GhalimLab LIMS - Logique d'interaction dynamique
 */

document.addEventListener("DOMContentLoaded", () => {
    // Initialisation des tooltips ou écouteurs
    console.log("GhalimLab LIMS initialisé avec succès.");
});

// Toast Notification
function showToast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.style.position = "fixed";
        container.style.bottom = "20px";
        container.style.right = "20px";
        container.style.zIndex = "9999";
        container.style.display = "flex";
        container.style.flexDirection = "column";
        container.style.gap = "10px";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.style.padding = "12px 18px";
    toast.style.borderRadius = "8px";
    toast.style.boxShadow = "0 4px 12px rgba(0,0,0,0.15)";
    toast.style.fontSize = "0.88rem";
    toast.style.fontWeight = "600";
    toast.style.display = "flex";
    toast.style.alignItems = "center";
    toast.style.gap = "8px";
    toast.style.transition = "all 0.3s ease";

    if (type === "success") {
        toast.style.backgroundColor = "#dcfce7";
        toast.style.color = "#15803d";
        toast.style.border = "1px solid #86efac";
        toast.innerHTML = `<span>✓</span> <span>${message}</span>`;
    } else if (type === "error") {
        toast.style.backgroundColor = "#fee2e2";
        toast.style.color = "#b91c1c";
        toast.style.border = "1px solid #fca5a5";
        toast.innerHTML = `<span>⚠</span> <span>${message}</span>`;
    } else {
        toast.style.backgroundColor = "#e0f2fe";
        toast.style.color = "#0369a1";
        toast.style.border = "1px solid #7dd3fc";
        toast.innerHTML = `<span>ℹ</span> <span>${message}</span>`;
    }

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Déclenchement de la simulation d'un automate (Sysmex ou Cobas)
async function triggerSimulation(automateType, barcode) {
    const btnId = `btn-sim-${automateType}`;
    const btn = document.getElementById(btnId);
    const originalText = btn ? btn.innerHTML : "";
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner">⏳</span> Transmission ASTM en cours...`;
    }

    try {
        const response = await fetch("/api/automates/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                automate: automateType,
                code_barres: barcode
            })
        });

        const data = await response.json();
        if (response.ok && data.status === "success") {
            showToast(`Transmission ${automateType.toUpperCase()} réussie pour ${barcode} (${data.frames_envoyees} trames ASTM) !`, "success");
            // Recharger la page après 1.2 seconde pour voir les résultats
            setTimeout(() => {
                window.location.reload();
            }, 1200);
        } else {
            showToast(`Erreur : ${data.detail || data.error || "Échec de simulation"}`, "error");
        }
    } catch (err) {
        showToast(`Erreur de connexion : ${err.message}`, "error");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}

// Validation Biologique du Dossier
async function validerDossierBiologique(demandeId) {
    const conclusion = document.getElementById("conclusion_biologique") ? document.getElementById("conclusion_biologique").value : "";
    const validePar = document.getElementById("valide_par") ? document.getElementById("valide_par").value : "Dr. M. GHALIM";

    const btn = document.getElementById("btn-valider-dossier");
    if (btn) btn.disabled = true;

    try {
        const response = await fetch(`/api/validation/${demandeId}/valider`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                conclusion_biologique: conclusion,
                valide_par: validePar
            })
        });

        const data = await response.json();
        if (response.ok) {
            showToast("Dossier validé biologiquement avec succès !", "success");
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showToast(`Erreur : ${data.detail || "Échec de validation"}`, "error");
            if (btn) btn.disabled = false;
        }
    } catch (err) {
        showToast(`Erreur : ${err.message}`, "error");
        if (btn) btn.disabled = false;
    }
}

// Déverrouillage d'un dossier
async function devaliderDossier(demandeId) {
    if (!confirm("Voulez-vous vraiment déverrouiller ce dossier pour modification ?")) return;

    try {
        const response = await fetch(`/api/validation/${demandeId}/devalider`, {
            method: "POST"
        });
        if (response.ok) {
            showToast("Dossier déverrouillé.", "info");
            setTimeout(() => window.location.reload(), 800);
        }
    } catch (err) {
        showToast(`Erreur : ${err.message}`, "error");
    }
}

// Ajout Manuel d'un Résultat
async function ajouterResultatManuel(demandeId) {
    const paramSelect = document.getElementById("nouveau_parametre_id");
    const valInput = document.getElementById("nouvelle_valeur");
    const autoSelect = document.getElementById("source_automate");

    if (!paramSelect || !valInput || !valInput.value.trim()) {
        showToast("Veuillez renseigner un paramètre et une valeur.", "error");
        return;
    }

    try {
        const response = await fetch(`/api/validation/${demandeId}/ajouter-resultat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                parameter_id: parseInt(paramSelect.value),
                valeur: valInput.value.trim(),
                automate_source: autoSelect ? autoSelect.value : "Manuel"
            })
        });

        const data = await response.json();
        if (response.ok) {
            showToast("Résultat ajouté avec succès !", "success");
            setTimeout(() => window.location.reload(), 800);
        } else {
            showToast(`Erreur : ${data.detail || "Échec d'enregistrement"}`, "error");
        }
    } catch (err) {
        showToast(`Erreur : ${err.message}`, "error");
    }
}
