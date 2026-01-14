let currentIntent = null;
let currentMarkdown = null;
let currentPostId = null;
let currentRevisions = [];
let currentEditMode = "free";
let currentStatus = null;
let currentLastRevisionId = null;
let suggestedTitleValue = "";
let titleCommitted = false;
let isEditingContent = false;
let editRequestInFlight = false;
let policyEditInFlight = false;
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
  const target = $("suggested-title-text");
  if (target) {
    target.textContent = title || "";
  }
}

function setSuggestedTitleValue(title) {
  suggestedTitleValue = (title || "").trim();
  setSuggestedTitle(suggestedTitleValue ? `Suggested title: ${suggestedTitleValue}` : "");
  const titleInput = $("title-input");
  if (titleInput && suggestedTitleValue && !titleCommitted && !titleInput.value.trim()) {
    titleInput.value = suggestedTitleValue;
  }
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
  const canEnable = enabled && currentEditMode === "metadata";
  if (input) input.disabled = !canEnable;
  if (btn) btn.disabled = !canEnable;
}

function setEditControlsEnabled(enabled) {
  const editBtn = $("edit-content-btn");
  const applyBtn = $("apply-edit-btn");
  const canEnable = enabled && currentEditMode === "free";
  if (editBtn) editBtn.disabled = !canEnable;
  if (applyBtn) applyBtn.disabled = !canEnable;
}

function setPolicyEditControlsEnabled(enabled) {
  const policyText = $("policy-text");
  const runBtn = $("run-policy-edit-btn");
  const canEnable = enabled && currentEditMode === "policy";
  if (policyText) policyText.disabled = !canEnable;
  if (runBtn) runBtn.disabled = !canEnable;
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
  applyEditModeState();
}

function setGatedActionsEnabled(enabled) {
  const btn = $("save-document-btn");
  if (btn) btn.disabled = !enabled;
}

function updateSuggestedTitleAction() {
  const button = $("use-suggested-title");
  const shouldShow = !!suggestedTitleValue && !titleCommitted;
  if (button) {
    button.hidden = !shouldShow;
    button.disabled = !shouldShow;
  }
}

function setInvariantIndicators(status, lastRevisionId) {
  const statusTarget = $("post-status-indicator");
  const revisionTarget = $("post-revision-indicator");
  if (statusTarget) {
    statusTarget.textContent = `Status: ${status || "—"}`;
  }
  if (revisionTarget) {
    const label = typeof lastRevisionId === "number" ? String(lastRevisionId) : "—";
    revisionTarget.textContent = `Last revision: ${label}`;
  }
}

function renderDraftPosts(draftPosts) {
  const list = $("draft-post-list");
  if (!list) return;
  list.textContent = "";
  if (!Array.isArray(draftPosts) || !draftPosts.length) {
    const item = document.createElement("li");
    item.textContent = "No draft posts available.";
    list.appendChild(item);
    return;
  }
  draftPosts.forEach((post) => {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = `/blog/editor?post_id=${encodeURIComponent(post.post_id)}`;
    link.textContent = post.title || "(untitled)";
    item.appendChild(link);
    if (post.created_at) {
      const meta = document.createElement("div");
      meta.textContent = `Created: ${post.created_at}`;
      item.appendChild(meta);
    }
    list.appendChild(item);
  });
}

function showEditorEntry() {
  const entry = $("editor-entry");
  if (entry) {
    entry.hidden = false;
  }
  const intentContainer = $("intent-container");
  if (intentContainer) {
    intentContainer.hidden = true;
  }
  setView("intent");
}

function showIntentEntry() {
  const entry = $("editor-entry");
  if (entry) {
    entry.hidden = true;
  }
  const intentContainer = $("intent-container");
  if (intentContainer) {
    intentContainer.hidden = false;
  }
  setView("intent");
}

function updateEditModeButtons() {
  const freeBtn = $("mode-free-edit");
  const policyBtn = $("mode-policy-edit");
  const metaBtn = $("mode-metadata-edit");
  const setActive = (btn, active) => {
    if (!btn) return;
    btn.setAttribute("aria-pressed", active ? "true" : "false");
    btn.classList.toggle("btn--primary", active);
    btn.classList.toggle("btn--ghost", !active);
    btn.classList.toggle("active", active);
  };
  setActive(freeBtn, currentEditMode === "free");
  setActive(policyBtn, currentEditMode === "policy");
  setActive(metaBtn, currentEditMode === "metadata");
}

function applyEditModeState() {
  const isFree = currentEditMode === "free";
  const isPolicy = currentEditMode === "policy";
  const isMetadata = currentEditMode === "metadata";
  const hasPost = !!currentPostId;
  const canEdit = isFree && hasPost && !editRequestInFlight;
  const canPolicyEdit = isPolicy && hasPost && !policyEditInFlight;
  setEditControlsEnabled(canEdit);
  const editor = $("article-editor");
  if (editor) editor.disabled = !isFree;
  const policyText = $("policy-text");
  if (policyText) policyText.disabled = !isPolicy;
  const runBtn = $("run-policy-edit-btn");
  if (runBtn) runBtn.disabled = !canPolicyEdit;
  const titleEnabled = isMetadata && hasPost;
  setTitleControlsEnabled(titleEnabled);
  const authorInput = $("author-input");
  const authorBtn = $("set-author-btn");
  if (authorInput) authorInput.disabled = !titleEnabled;
  if (authorBtn) authorBtn.disabled = !titleEnabled;
}

function setCurrentEditMode(mode) {
  if (mode !== "free" && mode !== "policy" && mode !== "metadata") {
    return;
  }
  currentEditMode = mode;
  updateEditModeButtons();
  applyEditModeState();
}

async function applySuggestedTitle() {
  const button = $("use-suggested-title");
  if (!button) return;
  if (!suggestedTitleValue) {
    return;
  }
  if (!currentPostId) {
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
    setError("No intent to download. Load or apply changes first.");
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
      setError(detail || "Failed to download intent.");
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
    setError(err?.message || "Error downloading intent.");
  }
}

async function generateBlogPost() {
  if (!currentPostId) {
    setError("No post available to generate from.");
    return;
  }
  if (!currentIntent) {
    setError("No intent to generate from. Load or apply changes first.");
    return;
  }
  setIntentDisabled(true);
  setArticleStatus("Generating…");
  setSuggestedTitleValue("");
  setFinalTitle("");
  setPolicyEditStatus("");
  setPolicyEditResult("");
  titleCommitted = false;
  setEditMode(false);
  setEditControlsEnabled(false);
  setEditRequestState(false);
  setPolicyEditControlsEnabled(false);
  setPolicyEditStatus("");
  setPolicyEditResult("");
  policyEditInFlight = false;
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
    setPolicyEditControlsEnabled(!!currentPostId);
    applyEditModeState();
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
  const canStartEdit = !!currentPostId && !editRequestInFlight && isEditingContent;
  setEditRequestState(true);
  try {
    if (!canStartEdit) {
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
  } finally {
    setEditRequestState(false);
  }
}

async function runPolicyEdit() {
  const canStartPolicyEdit = !!currentPostId && !policyEditInFlight;
  policyEditInFlight = true;
  setPolicyEditControlsEnabled(false);
  setPolicyEditStatus("editing…");
  setPolicyEditResult("");
  try {
    if (!canStartPolicyEdit) {
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
  } finally {
    policyEditInFlight = false;
    applyEditModeState();
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

async function createNewPostFromIntent() {
  if (!currentIntent) {
    setError("No intent to generate from. Load or apply changes first.");
    return;
  }
  try {
    const resp = await fetch("/blog/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent: currentIntent }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      setError(detail || "Failed to create post.");
      return;
    }
    const data = await resp.json();
    if (data?.post_id) {
      window.location.href = `/blog/editor?post_id=${encodeURIComponent(data.post_id)}`;
    } else {
      setError("Failed to create post.");
    }
  } catch (err) {
    setError(err?.message || "Failed to create post.");
  }
}

async function createBlogPostFromIntent(intentObject) {
  if (!intentObject) {
    setError("No intent to generate from. Load or apply changes first.");
    return;
  }
  try {
    const resp = await fetch("/blog/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent: intentObject }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      setError(detail || "Failed to create post.");
      return;
    }
    const data = await resp.json();
    if (data?.post_id) {
      window.location = `/blog/editor?post_id=${encodeURIComponent(data.post_id)}`;
    } else {
      setError("Failed to create post.");
    }
  } catch (err) {
    setError(err?.message || "Failed to create post.");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const queryPostId = new URLSearchParams(window.location.search).get("post_id");
  const queryMode = new URLSearchParams(window.location.search).get("mode");
  const isEditorEntry = window.location.pathname === "/blog/editor";
  if (queryPostId) {
    loadExistingDraft(queryPostId);
  }
  const intentContainer = $("intent-container");
  if (!queryPostId && isEditorEntry && queryMode === "create") {
    showIntentEntry();
  } else if (!queryPostId && isEditorEntry) {
    showEditorEntry();
  } else if (!queryPostId) {
    showIntentEntry();
  }
  if (queryPostId && intentContainer) {
    intentContainer.hidden = true;
  }
  const createFromIntentBtn = $("create-from-intent-btn");
  if (createFromIntentBtn) {
    createFromIntentBtn.addEventListener("click", () => {
      showIntentEntry();
    });
  }
  const input = $("intent-file");
  if (input) {
    input.addEventListener("change", uploadIntent);
  }
  const intentForm = $("intent-form");
  if (intentForm) {
    intentForm.addEventListener("input", applyIntentChanges);
    intentForm.addEventListener("submit", (event) => {
      event.preventDefault();
      createBlogPostFromIntent(readIntentFromForm());
    });
  }
  const generateBtn = $("generate-blog-post-btn");
  if (generateBtn) {
    generateBtn.addEventListener("click", () => {
      createBlogPostFromIntent(readIntentFromForm());
    });
  }
  $("set-title-btn")?.addEventListener("click", setTitle);
  $("use-suggested-title")?.addEventListener("click", applySuggestedTitle);
  $("edit-content-btn")?.addEventListener("click", toggleEditContent);
  $("apply-edit-btn")?.addEventListener("click", applyEdit);
  $("run-policy-edit-btn")?.addEventListener("click", runPolicyEdit);
  $("mode-free-edit")?.addEventListener("click", () => setCurrentEditMode("free"));
  $("mode-policy-edit")?.addEventListener("click", () => setCurrentEditMode("policy"));
  $("mode-metadata-edit")?.addEventListener("click", () => setCurrentEditMode("metadata"));
  if (!queryPostId && !isEditorEntry) {
    setArticleStatus("No blog post generated yet. Click Generate Blog Post.");
  }
  setTitleControlsEnabled(false);
  setEditControlsEnabled(false);
  setEditMode(false);
  setGatedActionsEnabled(false);
  setPolicyEditControlsEnabled(false);
  setPolicyEditStatus("");
  setPolicyEditResult("");
  policyEditInFlight = false;
  updateEditModeButtons();
  applyEditModeState();
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

async function loadExistingDraft(postId) {
  try {
    const resp = await fetch(`/blog/editor/data?post_id=${encodeURIComponent(postId)}`);
    if (!resp.ok) {
      const detail = await resp.text();
      setError(detail || "Failed to load post.");
      return;
    }
    const data = await resp.json();
    currentIntent = null;
    const editorEntry = $("editor-entry");
    if (editorEntry) {
      editorEntry.hidden = true;
    }
    const intentContainer = $("intent-container");
    if (intentContainer) {
      intentContainer.hidden = true;
    }
    currentPostId = data.post_id || null;
    currentMarkdown = data.content || "";
    currentStatus = data.status || null;
    currentLastRevisionId = data.last_revision_id ?? null;
    currentRevisions = Array.isArray(data.revisions) ? data.revisions : [];
    const articleArea = $("article-text");
    if (articleArea) {
      articleArea.innerHTML = marked.parse(currentMarkdown);
    }
    if (!currentMarkdown.trim()) {
      setEditMode(true);
    }
    const titleInput = $("title-input");
    if (titleInput) {
      titleInput.value = data?.meta?.title || "";
    }
    const authorInput = $("author-input");
    if (authorInput) {
      authorInput.value = data?.meta?.author || "";
    }
    setSuggestedTitleValue("");
    setFinalTitle("");
    if (currentMarkdown.trim()) {
      setEditMode(false);
    }
    setView("content");
    setEditRequestState(false);
    policyEditInFlight = false;
    setPolicyEditControlsEnabled(!!currentPostId);
    setTitleControlsEnabled(!!currentPostId);
    setEditControlsEnabled(!!currentPostId);
    setPolicyEditControlsEnabled(!!currentPostId);
    setGatedActionsEnabled(!!currentPostId);
    setInvariantIndicators(currentStatus, currentLastRevisionId);
    applyEditModeState();
    setError("");
  } catch (err) {
    setError(err?.message || "Error loading post.");
  }
}

function resetPostView() {
  currentMarkdown = null;
  currentPostId = null;
  currentStatus = null;
  currentLastRevisionId = null;
  suggestedTitleValue = "";
  titleCommitted = false;
  isEditingContent = false;
  editRequestInFlight = false;
  policyEditInFlight = false;
  const article = $("article-text");
  if (article) {
    article.textContent = "";
  }
  const editor = $("article-editor");
  if (editor) {
    editor.value = "";
  }
  const policyText = $("policy-text");
  if (policyText) {
    policyText.value = "";
  }
  setError("");
  setArticleStatus("No blog post generated yet. Click Generate Blog Post.");
  setSuggestedTitleValue("");
  setFinalTitle("");
  setTitleControlsEnabled(false);
  setEditControlsEnabled(false);
  setEditMode(false);
  setGatedActionsEnabled(false);
  setPolicyEditControlsEnabled(false);
  setPolicyEditStatus("");
  setPolicyEditResult("");
  setInvariantIndicators(null, null);
  setView("intent");
}

function clearIntent() {
  isClearing = true;
  currentIntent = null;
  currentMarkdown = null;
  currentPostId = null;
  currentStatus = null;
  currentLastRevisionId = null;
  suggestedTitleValue = "";
  titleCommitted = false;
  isEditingContent = false;
  editRequestInFlight = false;
  policyEditInFlight = false;
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
  const policyText = $("policy-text");
  if (policyText) {
    policyText.value = "";
  }
  setError("");
  setArticleStatus("");
  setSuggestedTitleValue("");
  setFinalTitle("");
  setTitleControlsEnabled(false);
  setEditControlsEnabled(false);
  setGatedActionsEnabled(false);
  setPolicyEditControlsEnabled(false);
  setPolicyEditStatus("");
  setPolicyEditResult("");
  setInvariantIndicators(null, null);
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
