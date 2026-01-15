let currentMarkdown = null;
let currentPostId = null;
let suggestedTitleValue = "";
let isEditingContent = false;

function $(id) {
  return document.getElementById(id);
}

const errorArea = $("error-area");

function setError(message) {
  if (errorArea) {
    errorArea.textContent = message || "";
  }
}

// Intent load/save is a local convenience only.
// It must never influence submission, validation, or generation.
async function resolveYamlParser() {
  if (window.jsyaml && typeof window.jsyaml.load === "function") {
    return window.jsyaml;
  }
  if (window.YAML && typeof window.YAML.parse === "function" && typeof window.YAML.stringify === "function") {
    return window.YAML;
  }
  const module = await import("https://cdn.jsdelivr.net/npm/js-yaml@4.1.0/+esm");
  return module;
}

async function downloadIntentFromForm(filename) {
  const documentGoalRaw = $("document-goal")?.value ?? "";
  const audienceRaw = $("audience")?.value ?? "";
  const toneRaw = $("tone")?.value ?? "";
  const requiredSectionsRaw = $("required-sections")?.value ?? "";
  const forbiddenSectionsRaw = $("forbidden-sections")?.value ?? "";
  const mustIncludeRaw = $("must-include")?.value ?? "";
  const mustAvoidRaw = $("must-avoid")?.value ?? "";
  const requiredMentionsRaw = $("required-mentions")?.value ?? "";
  const humorLevelRaw = $("humor-level")?.value ?? "";
  const formalityRaw = $("formality")?.value ?? "";
  const narrativeVoiceRaw = $("narrative-voice")?.value ?? "";

  const toScalar = (value) => {
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
  };

  const toList = (value) =>
    value
      .split(/\n/)
      .map((line) => line.trim())
      .filter(Boolean);

  const intentPayload = {
    structural_intent: {
      document_goal: toScalar(documentGoalRaw),
      audience: toScalar(audienceRaw),
      tone: toScalar(toneRaw),
      required_sections: toList(requiredSectionsRaw),
      forbidden_sections: toList(forbiddenSectionsRaw),
    },
    semantic_constraints: {
      must_include: toList(mustIncludeRaw),
      must_avoid: toList(mustAvoidRaw),
      required_mentions: toList(requiredMentionsRaw),
    },
    stylistic_preferences: {
      humor_level: toScalar(humorLevelRaw),
      formality: toScalar(formalityRaw),
      narrative_voice: toScalar(narrativeVoiceRaw),
    },
  };

  const parser = await resolveYamlParser();
  const yamlText =
    typeof parser.dump === "function"
      ? parser.dump(intentPayload, { sortKeys: false })
      : parser.stringify(intentPayload);

  const blob = new Blob([yamlText], { type: "text/yaml" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || "intent.yaml";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

async function loadIntentIntoForm(yamlText) {
  let parsed = {};
  try {
    const parser = await resolveYamlParser();
    parsed = typeof parser.load === "function" ? parser.load(yamlText) || {} : parser.parse(yamlText) || {};
  } catch (err) {
    console.error("Failed to load intent YAML.");
    return;
  }

  const structural = parsed.structural_intent || {};
  const semantic = parsed.semantic_constraints || {};
  const stylistic = parsed.stylistic_preferences || {};

  const setValue = (id, value) => {
    const field = $(id);
    if (!field) return;
    field.value = value ?? "";
  };

  const setList = (id, value) => {
    const field = $(id);
    if (!field) return;
    field.value = Array.isArray(value) ? value.join("\n") : "";
  };

  setValue("document-goal", structural.document_goal ?? "");
  setValue("audience", structural.audience ?? "");
  setValue("tone", structural.tone ?? "");
  setList("required-sections", structural.required_sections);
  setList("forbidden-sections", structural.forbidden_sections);
  setList("must-include", semantic.must_include);
  setList("must-avoid", semantic.must_avoid);
  setList("required-mentions", semantic.required_mentions);
  setValue("humor-level", stylistic.humor_level ?? "");
  setValue("formality", stylistic.formality ?? "");
  setValue("narrative-voice", stylistic.narrative_voice ?? "");
}

function openIntentFile() {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".yaml,.yml";
  input.hidden = true;
  input.addEventListener("change", () => {
    const file = input.files && input.files[0];
    if (!file) {
      input.remove();
      return;
    }
    const reader = new FileReader();
    reader.onload = async () => {
      await loadIntentIntoForm(reader.result);
      input.remove();
    };
    reader.readAsText(file);
  });
  document.body.appendChild(input);
  input.click();
}

window.downloadIntentFromForm = downloadIntentFromForm;
window.openIntentFile = openIntentFile;

function openDownloadIntentModal() {
  const modal = $("download-intent-modal");
  const filenameInput = $("download-intent-filename");
  if (!modal || !filenameInput) {
    return;
  }
  filenameInput.value = "intent.yaml";
  modal.hidden = false;
  filenameInput.focus();
}

function closeDownloadIntentModal() {
  const modal = $("download-intent-modal");
  if (modal) {
    modal.hidden = true;
  }
}

function confirmDownloadIntent() {
  const filenameInput = $("download-intent-filename");
  const filename = (filenameInput?.value || "").trim() || "intent.yaml";
  downloadIntentFromForm(filename)
    .then(() => {
      setError("");
      closeDownloadIntentModal();
    })
    .catch((err) => {
      setError(err?.message || "Error downloading intent.");
    });
}

function setSuggestedTitle(title) {
  const target = $("suggested-title-text");
  if (target) {
    target.textContent = title || "";
  }
}

function setSuggestedTitleValue(title) {
  suggestedTitleValue = (title || "").trim();
  setSuggestedTitle(suggestedTitleValue ? `Suggested title: ${suggestedTitleValue}` : "");
  const titleInput = $("title-input");
  if (titleInput && suggestedTitleValue && !titleInput.value.trim()) {
    titleInput.value = suggestedTitleValue;
  }
}

function setFinalTitle(title) {
  const target = $("final-title");
  if (target) {
    target.textContent = title || "";
  }
}

function setPolicyEditStatus(text) {
  const target = $("policy-edit-status");
  if (target) {
    target.textContent = text || "";
  }
}

function setPolicyEditResult(text) {
  const target = $("policy-edit-result");
  if (target) {
    target.textContent = text || "";
  }
}

function setEditMode(enabled) {
  isEditingContent = enabled;
  const article = $("article-text");
  const editor = $("article-editor");
  const applyBtn = $("apply-edit-btn");
  const editBtn = $("edit-content-btn");
  if (editor) {
    if (enabled) editor.value = currentMarkdown || "";
  }
  if (editBtn) editBtn.textContent = enabled ? "Cancel edit" : "Edit content";
}

async function setTitle() {
  if (!currentPostId) {
    setError("No post available to set title.");
    return;
  }
  const input = $("title-input");
  const title = (input?.value || "").trim();
  if (!title) {
    setError("Title cannot be empty.");
    return;
  }
  try {
    const resp = await fetch("/blog/set-title", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: currentPostId, title }),
    });
    if (resp.status === 409) {
      setError("Title already set.");
      return;
    }
    if (!resp.ok) {
      const detail = await resp.text();
      setError(detail || "Failed to set title.");
      return;
    }
    const data = await resp.json();
    setFinalTitle(`Title: ${data.title}`);
    setError("");
  } catch (err) {
    setError(err?.message || "Error setting title.");
  }
}

async function setAuthor() {
  if (!currentPostId) {
    setError("No post available to set author.");
    return;
  }
  const input = $("author-input");
  const author = (input?.value || "").trim();
  if (!author) {
    setError("Author cannot be empty.");
    return;
  }
  try {
    const resp = await fetch("/blog/set-author", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: currentPostId, author }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      setError(detail || "Failed to set author.");
      return;
    }
    await resp.json();
    setError("");
  } catch (err) {
    setError(err?.message || "Error setting author.");
  }
}

function toggleEditContent() {
  if (!currentPostId) return;
  setEditMode(!isEditingContent);
}

async function applyEdit() {
  try {
    if (!currentPostId || !isEditingContent) {
      return;
    }
    const editor = $("article-editor");
    const rawContent = editor?.value || "";
    if (!rawContent.trim()) {
      setError("Content cannot be empty.");
      return;
    }
    const resp = await fetch("/blog/edit-content", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: currentPostId, content: rawContent }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      setError(detail || "Failed to apply edit.");
      return;
    }
    const data = await resp.json();
    currentMarkdown = data.content || "";
    const articleArea = $("article-text");
    if (articleArea) {
      articleArea.innerHTML = marked.parse(currentMarkdown);
    }
    setEditMode(false);
    setError("");
  } catch (err) {
    setError(err?.message || "Error applying edit.");
  }
}

async function runPolicyEdit() {
  setPolicyEditStatus("editing…");
  setPolicyEditResult("");
  try {
    if (!currentPostId) {
      return;
    }
    const policyText = $("policy-text");
    const policyValue = (policyText?.value || "").trim();
    if (!policyValue) {
      setPolicyEditStatus("Policy text is required.");
      return;
    }
    const resp = await fetch("/blog/edit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: currentPostId, policy_text: policyValue }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      setPolicyEditStatus(detail || "Edit failed.");
      return;
    }
    const data = await resp.json();
    currentMarkdown = data.content || "";
    const articleArea = $("article-text");
    if (articleArea) {
      articleArea.innerHTML = marked.parse(currentMarkdown);
    }
    const changed = (data.changed_chunks || []).join(", ");
    const rejected = (data.rejected_chunks || [])
      .map((item) => `${item.chunk_index}: ${item.reason}`)
      .join("\n");
    const resultLines = [
      `Revision: ${data.revision_id}`,
      `Changed chunks: ${changed || "none"}`,
    ];
    if (rejected) {
      resultLines.push(`Rejected:\n${rejected}`);
    }
    setPolicyEditStatus("edit applied");
    setPolicyEditResult(resultLines.join("\n"));
    if (policyText) {
      policyText.value = "";
    }
    setError("");
  } catch (err) {
    setPolicyEditStatus(err?.message || "Edit failed.");
  }
}

async function suggestTitle(content) {
  if (!content) {
    setSuggestedTitleValue("");
    return;
  }
  try {
    const resp = await fetch("/blog/suggest-title", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      setSuggestedTitleValue("");
      setError(detail || "Failed to suggest title.");
      return;
    }
    const data = await resp.json();
    const title = (data?.suggested_title || "").trim();
    setSuggestedTitleValue(title);
  } catch (err) {
    setSuggestedTitleValue("");
    setError(err?.message || "Failed to suggest title.");
  }
}

async function downloadDocument(filename) {
  const resp = await fetch("/document/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ markdown: currentMarkdown, filename }),
  });
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error(detail || "Failed to download document.");
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
}

function openDownloadModal() {
  const modal = $("download-modal");
  const filenameInput = $("download-filename");
  if (!modal || !filenameInput) {
    return;
  }
  filenameInput.value = "article.md";
  modal.hidden = false;
  filenameInput.focus();
}

function closeDownloadModal() {
  const modal = $("download-modal");
  if (modal) {
    modal.hidden = true;
  }
}

function confirmDownload() {
  const filenameInput = $("download-filename");
  const filename = (filenameInput?.value || "").trim() || "article.md";
  downloadDocument(filename)
    .then(() => {
      setError("");
      closeDownloadModal();
    })
    .catch((err) => {
      setError(err?.message || "Error downloading document.");
    });
}

document.addEventListener("DOMContentLoaded", () => {
  const postId = document.body?.dataset?.postId;
  if (!postId) {
    throw new Error("Missing required post_id data attribute on <body>.");
  }
  currentPostId = postId;

  // Initialize markdown rendering from preserved source
  const article = $("article-text");
  const articleSource = $("article-source");
  if (article && articleSource) {
    currentMarkdown = articleSource.value || "";
    article.innerHTML = marked.parse(currentMarkdown);
  }

  const intentForm = $("intent-form");
  if (intentForm) {
    intentForm.addEventListener("submit", () => {
      const generateBtn = $("generate-blog-post-btn");
      if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.textContent = "Generating…";
      }
    });
  }

  $("download-intent-btn")?.addEventListener("click", openDownloadIntentModal);
  $("download-intent-cancel-btn")?.addEventListener("click", closeDownloadIntentModal);
  $("download-intent-confirm-btn")?.addEventListener("click", confirmDownloadIntent);
  $("set-title-btn")?.addEventListener("click", setTitle);
  $("set-author-btn")?.addEventListener("click", setAuthor);
  $("edit-content-btn")?.addEventListener("click", toggleEditContent);
  $("apply-edit-btn")?.addEventListener("click", applyEdit);
  $("run-policy-edit-btn")?.addEventListener("click", runPolicyEdit);
  $("save-document-btn")?.addEventListener("click", openDownloadModal);
  $("download-cancel-btn")?.addEventListener("click", closeDownloadModal);
  $("download-confirm-btn")?.addEventListener("click", confirmDownload);
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

document.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-href]");
  if (!btn) return;
  window.location.href = btn.dataset.href;
});
