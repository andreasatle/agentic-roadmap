let currentPhase = "intent";
let currentIntent = null;
let currentMarkdown = null;

const intentFields = {
  document_goal: document.getElementById("document-goal"),
  audience: document.getElementById("audience"),
  tone: document.getElementById("tone"),
  required_sections: document.getElementById("required-sections"),
  forbidden_sections: document.getElementById("forbidden-sections"),
  must_include: document.getElementById("must-include"),
  must_avoid: document.getElementById("must-avoid"),
  required_mentions: document.getElementById("required-mentions"),
  humor_level: document.getElementById("humor-level"),
  formality: document.getElementById("formality"),
  narrative_voice: document.getElementById("narrative-voice"),
};

const errorArea = document.getElementById("error-area");

function renderIntent(intent) {
  const s = intent.structural_intent || {};
  const sem = intent.semantic_constraints || {};
  const sty = intent.stylistic_preferences || {};
  intentFields.document_goal.value = s.document_goal || "";
  intentFields.audience.value = s.audience || "";
  intentFields.tone.value = s.tone || "";
  intentFields.required_sections.value = (s.required_sections || []).join("\n");
  intentFields.forbidden_sections.value = (s.forbidden_sections || []).join("\n");
  intentFields.must_include.value = (sem.must_include || []).join("\n");
  intentFields.must_avoid.value = (sem.must_avoid || []).join("\n");
  intentFields.required_mentions.value = (sem.required_mentions || []).join("\n");
  intentFields.humor_level.value = sty.humor_level || "";
  intentFields.formality.value = sty.formality || "";
  intentFields.narrative_voice.value = sty.narrative_voice || "";
}

function setError(message) {
  errorArea.textContent = message || "";
}

function setIntentDisabled(flag) {
  Object.values(intentFields).forEach((el) => {
    if (el) {
      el.disabled = flag;
      el.classList.toggle("opacity-60", flag);
      el.classList.toggle("cursor-not-allowed", flag);
    }
  });
  const fileInput = document.getElementById("intent-file");
  if (fileInput) {
    fileInput.disabled = flag;
    fileInput.classList.toggle("opacity-60", flag);
    fileInput.classList.toggle("cursor-not-allowed", flag);
  }
  const generateBtn = document.getElementById("generate-document-btn");
  if (generateBtn) {
    generateBtn.disabled = flag;
    generateBtn.textContent = flag ? "Generating…" : "Generate Document";
    generateBtn.classList.toggle("bg-green-700", flag);
    generateBtn.classList.toggle("cursor-not-allowed", flag);
    generateBtn.classList.toggle("opacity-80", flag);
  }
}

function readIntentFromForm() {
  return {
    structural_intent: {
      document_goal: intentFields.document_goal.value.trim() || null,
      audience: intentFields.audience.value.trim() || null,
      tone: intentFields.tone.value.trim() || null,
      required_sections: intentFields.required_sections.value
        .split(/\n/)
        .map((s) => s.trim())
        .filter(Boolean),
      forbidden_sections: intentFields.forbidden_sections.value
        .split(/\n/)
        .map((s) => s.trim())
        .filter(Boolean),
    },
    semantic_constraints: {
      must_include: intentFields.must_include.value
        .split(/\n/)
        .map((s) => s.trim())
        .filter(Boolean),
      must_avoid: intentFields.must_avoid.value
        .split(/\n/)
        .map((s) => s.trim())
        .filter(Boolean),
      required_mentions: intentFields.required_mentions.value
        .split(/\n/)
        .map((s) => s.trim())
        .filter(Boolean),
    },
    stylistic_preferences: {
      humor_level: intentFields.humor_level.value.trim() || null,
      formality: intentFields.formality.value.trim() || null,
      narrative_voice: intentFields.narrative_voice.value.trim() || null,
    },
  };
}

function uploadIntent(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) {
    return;
  }
  const reader = new FileReader();
  reader.onload = async () => {
    try {
      const yamlText = reader.result;
      const resp = await fetch("/intent/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml_text: yamlText }),
      });
      if (!resp.ok) {
        const detail = await resp.text();
        setError(detail || "Failed to parse intent.");
        return;
      }
      const data = await resp.json();
      currentIntent = data;
      renderIntent(currentIntent);
      setError("");
    } catch (err) {
    setError(err?.message || "Error loading intent.");
  }
};
  reader.readAsText(file);
}

async function applyIntentChanges() {
  try {
    const intent = readIntentFromForm();
    currentIntent = intent;
    setError("");
  } catch (err) {
    setError(err?.message || "Failed to apply intent changes.");
  }
}

async function saveIntent() {
  if (!currentIntent) {
    setError("No intent to save. Load or apply changes first.");
    return;
  }
  try {
    const filenameInput = document.getElementById("intent-filename");
    const filenameRaw = (filenameInput?.value || "").trim();
    const filename = filenameRaw || "intent.yaml";
    const resp = await fetch("/intent/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent: currentIntent, filename }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      setError(detail || "Failed to save intent.");
      return;
    }
    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    setError("");
  } catch (err) {
    setError(err?.message || "Error saving intent.");
  }
}

async function generateDocument() {
  if (!currentIntent) {
    setError("No intent to generate from. Load or apply changes first.");
    return;
  }
  setIntentDisabled(true, { allowOutput: true });
  const articleArea = document.getElementById("article-text");
  if (articleArea) {
    articleArea.textContent = "Generating...";
  }
  try {
    const resp = await fetch("/document/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent: currentIntent }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      setError(detail || "Failed to generate document.");
      return;
    }
    const data = await resp.json();
    currentMarkdown = data.markdown || "";
    if (articleArea) {
      articleArea.innerHTML = marked.parse(data.markdown || "");
    }
    setActivePhase("content");
    setError("");
  } catch (err) {
    setError(err?.message || "Error generating document.");
  } finally {
    setIntentDisabled(false);
  }
}

async function saveDocument() {
  if (!currentMarkdown) {
    setError("No article to save. Generate first.");
    return;
  }
  try {
    const filenameInput = document.getElementById("article-filename");
    const filename = (filenameInput?.value || "").trim();
    const resp = await fetch("/document/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markdown: currentMarkdown, filename }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      setError(detail || "Failed to save article.");
      return;
    }
    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || "article.md";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    setError("");
  } catch (err) {
    setError(err?.message || "Error saving article.");
  }
}

function setActivePhase(phase) {
  currentPhase = phase;
  document.querySelectorAll("[data-phase]").forEach((el) => {
    el.style.display = el.dataset.phase === phase ? "block" : "none";
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("intent-file");
  if (input) {
    input.addEventListener("change", uploadIntent);
  }
  const intentForm = document.getElementById("intent-form");
  if (intentForm) {
    intentForm.addEventListener("input", applyIntentChanges);
  }
  setActivePhase("intent");
});
