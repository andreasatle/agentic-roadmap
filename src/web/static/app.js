let currentIntent = null;
let currentMarkdown = null;
let currentPostId = null;
let suggestedTitleValue = "";
let titleCommitted = false;
let isEditingContent = false;
let editRequestInFlight = false;
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
  const generateBtn = $("generate-blog-post-btn");
  if (generateBtn) {
    generateBtn.disabled = flag;
    generateBtn.textContent = flag ? "Generating…" : "Generate Blog Post";
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

function setSuggestedTitle(title) {
  const target = $("suggested-title");
  if (target) {
    target.textContent = title || "";
  }
}

function setSuggestedTitleValue(title) {
  suggestedTitleValue = (title || "").trim();
  setSuggestedTitle(suggestedTitleValue ? `Suggested title: ${suggestedTitleValue}` : "");
  updateSuggestedTitleAction();
}

function setFinalTitle(title) {
  const target = $("final-title");
  if (target) {
    target.textContent = title || "";
  }
}

function setTitleControlsEnabled(enabled) {
  const input = $("title-input");
  const btn = $("set-title-btn");
  if (input) input.disabled = !enabled;
  if (btn) btn.disabled = !enabled;
}

function setEditControlsEnabled(enabled) {
  const editBtn = $("edit-content-btn");
  const applyBtn = $("apply-edit-btn");
  if (editBtn) editBtn.disabled = !enabled;
  if (applyBtn) applyBtn.disabled = !enabled;
}

function setEditMode(enabled) {
  isEditingContent = enabled;
  const article = $("article-text");
  const editor = $("article-editor");
  const applyBtn = $("apply-edit-btn");
  const editBtn = $("edit-content-btn");
  if (article) article.hidden = enabled;
  if (editor) {
    editor.hidden = !enabled;
    if (enabled) editor.value = currentMarkdown || "";
  }
  if (applyBtn) applyBtn.hidden = !enabled;
  if (editBtn) editBtn.textContent = enabled ? "Cancel edit" : "Edit content";
}

function setEditRequestState(inFlight) {
  editRequestInFlight = inFlight;
  setEditControlsEnabled(!inFlight);
}

function setGatedActionsEnabled(enabled) {
  const btn = $("save-document-btn");
  if (btn) btn.disabled = !enabled;
}

function updateSuggestedTitleAction() {
  const wrapper = $("suggested-title-action");
  const checkbox = $("use-suggested-title");
  const shouldShow = !!suggestedTitleValue && !titleCommitted;
  if (wrapper) wrapper.hidden = !shouldShow;
  if (checkbox) checkbox.disabled = !shouldShow;
}

async function applySuggestedTitle() {
  const checkbox = $("use-suggested-title");
  if (!checkbox || !checkbox.checked) return;
  if (!suggestedTitleValue) {
    checkbox.checked = false;
    return;
  }
  if (!currentPostId) {
    checkbox.checked = false;
    setError("No post available to set title.");
    return;
  }
  try {
    const resp = await fetch("/blog/set-title", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: currentPostId, title: suggestedTitleValue }),
    });
    if (resp.status === 409) {
      titleCommitted = true;
      setTitleControlsEnabled(false);
      setGatedActionsEnabled(true);
      updateSuggestedTitleAction();
      return;
    }
    if (!resp.ok) {
      checkbox.checked = false;
      const detail = await resp.text();
      setError(detail || "Failed to set title.");
      return;
    }
    const data = await resp.json();
    titleCommitted = true;
    setFinalTitle(`Title: ${data.title}`);
    setTitleControlsEnabled(false);
    setGatedActionsEnabled(true);
    updateSuggestedTitleAction();
    setError("");
  } catch (err) {
    checkbox.checked = false;
    setError(err?.message || "Error setting title.");
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

async function generateBlogPost() {
  if (!currentIntent) {
    setError("No intent to generate from. Load or apply changes first.");
    return;
  }
  setIntentDisabled(true);
  setArticleStatus("Generating…");
  setSuggestedTitleValue("");
  setFinalTitle("");
  titleCommitted = false;
  setEditMode(false);
  setEditControlsEnabled(false);
  setEditRequestState(false);
  setGatedActionsEnabled(false);
  isGenerating = true;
  try {
    const resp = await fetch("/blog/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent: currentIntent }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      setArticleStatus("Failed to generate blog post. See error.");
      setError(detail || "Failed to generate blog post.");
      return;
    }
    const data = await resp.json();
    currentPostId = data.post_id || null;
    currentMarkdown = data.content || "";
    const articleArea = $("article-text");
    if (articleArea) {
      articleArea.innerHTML = marked.parse(currentMarkdown);
    }
    setEditMode(false);
    setView("content");
    if (data.suggested_title) {
      setSuggestedTitleValue(data.suggested_title);
    } else {
      suggestTitle(currentMarkdown);
    }
    setTitleControlsEnabled(!!currentPostId);
    setEditControlsEnabled(!!currentPostId);
    setError("");
  } catch (err) {
    setArticleStatus("Failed to generate blog post. See error.");
    setError(err?.message || "Error generating blog post.");
  } finally {
    isGenerating = false;
    setIntentDisabled(false);
  }
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
      titleCommitted = true;
      setError("Title already set.");
      setTitleControlsEnabled(false);
      setGatedActionsEnabled(true);
      updateSuggestedTitleAction();
      return;
    }
    if (!resp.ok) {
      const detail = await resp.text();
      setError(detail || "Failed to set title.");
      return;
    }
    const data = await resp.json();
    titleCommitted = true;
    setFinalTitle(`Title: ${data.title}`);
    setTitleControlsEnabled(false);
    setGatedActionsEnabled(true);
    updateSuggestedTitleAction();
    setError("");
  } catch (err) {
    setError(err?.message || "Error setting title.");
  }
}

function toggleEditContent() {
  if (!currentPostId || editRequestInFlight) return;
  setEditMode(!isEditingContent);
}

async function applyEdit() {
  if (!currentPostId || editRequestInFlight) return;
  if (!isEditingContent) return;
  const editor = $("article-editor");
  const rawContent = editor?.value || "";
  if (!rawContent.trim()) {
    setError("Content cannot be empty.");
    return;
  }
  setEditRequestState(true);
  try {
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
  } finally {
    setEditRequestState(false);
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
      setSuggestedTitleValue("");
      return;
    }
    const data = await resp.json();
    const title = (data?.suggested_title || "").trim();
    setSuggestedTitleValue(title);
  } catch (err) {
    setSuggestedTitleValue("");
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
  $("set-title-btn")?.addEventListener("click", setTitle);
  $("use-suggested-title")?.addEventListener("change", applySuggestedTitle);
  $("edit-content-btn")?.addEventListener("click", toggleEditContent);
  $("apply-edit-btn")?.addEventListener("click", applyEdit);
  setView("intent");
  setArticleStatus("No blog post generated yet. Click Generate Blog Post.");
  setTitleControlsEnabled(false);
  setEditControlsEnabled(false);
  setEditMode(false);
  setGatedActionsEnabled(false);
  updateSuggestedTitleAction();
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

function resetPostView() {
  currentMarkdown = null;
  currentPostId = null;
  suggestedTitleValue = "";
  titleCommitted = false;
  isEditingContent = false;
  editRequestInFlight = false;
  const article = $("article-text");
  if (article) {
    article.textContent = "";
  }
  const editor = $("article-editor");
  if (editor) {
    editor.value = "";
  }
  setError("");
  setArticleStatus("No blog post generated yet. Click Generate Blog Post.");
  setSuggestedTitleValue("");
  setFinalTitle("");
  setTitleControlsEnabled(false);
  setEditControlsEnabled(false);
  setEditMode(false);
  setGatedActionsEnabled(false);
  setView("intent");
}

function clearIntent() {
  isClearing = true;
  currentIntent = null;
  currentMarkdown = null;
  currentPostId = null;
  suggestedTitleValue = "";
  titleCommitted = false;
  isEditingContent = false;
  editRequestInFlight = false;
  setEditMode(false);
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
  setSuggestedTitleValue("");
  setFinalTitle("");
  setTitleControlsEnabled(false);
  setEditControlsEnabled(false);
  setGatedActionsEnabled(false);
  setView("intent");
  isClearing = false;
}

window.clearIntent = clearIntent;
window.resetPostView = resetPostView;

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
