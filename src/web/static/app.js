let currentIntent = null;
let currentMarkdown = null;
let currentView = "intent";
let isGenerating = false;
let isClearing = false;

function $(id) {
  return document.getElementById(id);
}

const intentFields = {
  document_goal: $("document-goal"),
  audience: $("audience"),
  tone: $("tone"),
  required_sections: $("required-sections"),
  forbidden_sections: $("forbidden-sections"),
  must_include: $("must-include"),
  must_avoid: $("must-avoid"),
  required_mentions: $("required-mentions"),
  humor_level: $("humor-level"),
  formality: $("formality"),
  narrative_voice: $("narrative-voice"),
};

const errorArea = $("error-area");

function setError(message) {
  if (errorArea) {
    errorArea.textContent = message || "";
  }
}

function setIntentDisabled(flag) {
  Object.values(intentFields).forEach((el) => {
    if (el) {
      el.disabled = flag;
      el.classList.toggle("opacity-60", flag);
      el.classList.toggle("cursor-not-allowed", flag);
    }
  });
  const fileInput = $("intent-file");
  if (fileInput) {
    fileInput.disabled = flag;
    fileInput.classList.toggle("opacity-60", flag);
    fileInput.classList.toggle("cursor-not-allowed", flag);
  }
  const generateBtn = $("generate-document-btn");
  if (generateBtn) {
    generateBtn.disabled = flag;
    generateBtn.textContent = flag ? "Generating…" : "Generate Document";
    generateBtn.classList.toggle("bg-green-700", flag);
    generateBtn.classList.toggle("cursor-not-allowed", flag);
    generateBtn.classList.toggle("opacity-80", flag);
  }
}

function setArticleStatus(text) {
  const article = $("article-text");
  if (article) {
    article.textContent = text;
  }
}

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
  if (isClearing) return;
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
    const filenameInput = $("intent-filename");
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
  setIntentDisabled(true);
  setView("content");
  setArticleStatus("Generating…");
  isGenerating = true;
  try {
    const resp = await fetch("/document/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent: currentIntent }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      setArticleStatus("Failed to generate document. See error.");
      setError(detail || "Failed to generate document.");
      setView("intent");
      return;
    }
    const data = await resp.json();
    currentMarkdown = data.markdown || "";
    const articleArea = $("article-text");
    if (articleArea) {
      articleArea.innerHTML = marked.parse(currentMarkdown);
    }
    setError("");
  } catch (err) {
    setArticleStatus("Failed to generate document. See error.");
    setError(err?.message || "Error generating document.");
    setView("intent");
  } finally {
    isGenerating = false;
    setIntentDisabled(false);
  }
}

async function saveDocument() {
  if (!currentMarkdown) {
    setError("No article to save. Generate first.");
    return;
  }
  try {
    const filenameInput = $("article-filename");
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

document.addEventListener("DOMContentLoaded", () => {
  const input = $("intent-file");
  if (input) {
    input.addEventListener("change", uploadIntent);
  }
  const intentForm = $("intent-form");
  if (intentForm) {
    intentForm.addEventListener("input", applyIntentChanges);
  }
  $("to-content")?.addEventListener("click", () => setView("content"));
  $("to-intent")?.addEventListener("click", () => setView("intent"));
  setView("intent");
  setArticleStatus("No document generated yet. Click Generate Document.");
});

document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  if (!target.classList.contains("intent-help")) return;
  const help = target.getAttribute("data-help");
  if (help) {
    showHelp(target, help);
  }
});

function setView(view) {
  const intent = document.getElementById("intent-view");
  const content = document.getElementById("content-view");

  if (!intent || !content) return;

  intent.hidden = view !== "intent";
  content.hidden = view !== "content";
}

function clearIntent() {
  isClearing = true;
  currentIntent = null;
  currentMarkdown = null;
  Object.values(intentFields).forEach((el) => {
    if (el) {
      el.value = "";
    }
  });
  const fileInput = $("intent-file");
  if (fileInput) {
    fileInput.value = "";
  }
  setError("");
  setArticleStatus("");
  setView("intent");
  isClearing = false;
}

window.clearIntent = clearIntent;

function openIntentFile() {
  const fileInput = $("intent-file");
  if (fileInput) {
    fileInput.click();
  }
}

window.openIntentFile = openIntentFile;

function showHelp(anchor, text) {
  const existing = document.querySelector(".help-tooltip");
  if (existing) {
    existing.remove();
    if (existing._anchor === anchor) return;
  }

  const tip = document.createElement("div");
  tip.className = "help-tooltip";
  tip.textContent = text;
  tip._anchor = anchor;

  document.body.appendChild(tip);

  const rect = anchor.getBoundingClientRect();
  const width = 320;
  const margin = 12;

  let left = rect.left + window.scrollX;
  const maxLeft = window.scrollX + window.innerWidth - width - margin;
  if (left > maxLeft) left = maxLeft;

  tip.style.top = `${rect.bottom + 6 + window.scrollY}px`;
  tip.style.left = `${Math.max(left, margin + window.scrollX)}px`;

  function cleanup(e) {
    if (anchor.contains(e.target)) return;
    tip.remove();
    document.removeEventListener("click", cleanup);
  }

  setTimeout(() => document.addEventListener("click", cleanup), 0);
}
