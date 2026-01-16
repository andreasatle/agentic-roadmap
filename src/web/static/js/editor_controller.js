import { $ } from "./dom.js";
import {
  applyContentEdit as applyContentEditAction,
  downloadDocument as downloadDocumentAction,
  fetchEditorData,
  runPolicyEdit as runPolicyEditAction,
  setAuthor as setAuthorAction,
  setTitle as setTitleAction,
  suggestTitle as suggestTitleAction,
} from "./editor_actions.js";
import { closeModal, openModal } from "./modals.js";

export function initEditorController() {

  function getPostId() {
    return document.body?.dataset?.postId || null;
  }

  function getMarkdown() {
    return $("article-source")?.value ?? "";
  }

  function setMarkdown(value) {
    const source = $("article-source");
    if (source) {
      source.value = value || "";
    }
  }

  function isEditingContent() {
    const editBtn = $("edit-content-btn");
    return editBtn?.textContent === "Cancel edit";
  }

  function getSuggestedTitleValue() {
    const wrap = $("suggested-title-wrap");
    const target = $("suggested-title-text");
    return wrap?.dataset?.suggestedTitle ?? target?.dataset?.suggestedTitle ?? "";
  }

  function setError(message) {
    const errorArea = $("error-area");
    if (errorArea) {
      errorArea.textContent = message || "";
    }
  }

  function setSuggestedTitleValue(title) {
    const value = (title || "").trim();
    const target = $("suggested-title-text");
    const wrap = $("suggested-title-wrap");
    if (wrap) {
      wrap.dataset.suggestedTitle = value;
    } else if (target) {
      target.dataset.suggestedTitle = value;
    }
    if (target) {
      target.textContent = value ? `Suggested: "${value}"` : "";
    }
    if (wrap) {
      wrap.hidden = !value;
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
    const editor = $("article-editor");
    const editBtn = $("edit-content-btn");
    if (editor) {
      if (enabled) editor.value = getMarkdown() || "";
    }
    if (editBtn) editBtn.textContent = enabled ? "Cancel edit" : "Edit content";
  }

  async function setTitle() {
    if (!getPostId()) {
      setError("No post available to set title.");
      return;
    }
    const input = $("title-modal-input");
    const title = (input?.value || "").trim();
    if (!title) {
      setError("Title cannot be empty.");
      return;
    }
    try {
      const result = await setTitleAction(getPostId(), title);
      if (!result.ok) {
        if (result.status === 409) {
          setError("Title already set.");
          return;
        }
        if (result.status !== null) {
          setError(result.error || "Failed to set title.");
          return;
        }
        setError(result.error || "Error setting title.");
        return;
      }
      const titleDisplay = $("title-display");
      if (titleDisplay) {
        titleDisplay.textContent = title;
      }
      setSuggestedTitleValue("");
      closeTitleModal();
      setError("");
    } catch (err) {
      setError(err?.message || "Error setting title.");
    }
  }

  async function setAuthor() {
    if (!getPostId()) {
      setError("No post available to set author.");
      return;
    }
    const input = $("author-modal-input");
    const author = (input?.value || "").trim();
    if (!author) {
      setError("Author cannot be empty.");
      return;
    }
    try {
      const result = await setAuthorAction(getPostId(), author);
      if (!result.ok) {
        if (result.status !== null) {
          setError(result.error || "Failed to set author.");
          return;
        }
        setError(result.error || "Error setting author.");
        return;
      }
      const authorDisplay = $("author-display");
      if (authorDisplay) {
        authorDisplay.textContent = author;
      }
      closeAuthorModal();
      setError("");
    } catch (err) {
      setError(err?.message || "Error setting author.");
    }
  }

  function openTitleModal() {
    openModal("title-modal", "title-modal-input");
    const modal = $("title-modal");
    if (modal) {
      if (!modal._escapeHandler) {
        modal._escapeHandler = (event) => {
          if (event.key === "Escape") {
            closeTitleModal();
          }
        };
      }
      modal.addEventListener("keydown", modal._escapeHandler);
    }
    setSuggestedTitleValue("");
    const editor = $("article-editor");
    const source = isEditingContent() && editor ? editor.value : getMarkdown();
    if (source) {
      suggestTitle(source);
    }
  }

  function closeTitleModal() {
    setSuggestedTitleValue("");
    const modal = $("title-modal");
    if (modal && modal._escapeHandler) {
      modal.removeEventListener("keydown", modal._escapeHandler);
    }
    closeModal("title-modal");
  }

  function openAuthorModal() {
    openModal("author-modal", "author-modal-input");
    const modal = $("author-modal");
    if (modal) {
      if (!modal._escapeHandler) {
        modal._escapeHandler = (event) => {
          if (event.key === "Escape") {
            closeAuthorModal();
          }
        };
      }
      modal.addEventListener("keydown", modal._escapeHandler);
    }
  }

  function closeAuthorModal() {
    const modal = $("author-modal");
    if (modal && modal._escapeHandler) {
      modal.removeEventListener("keydown", modal._escapeHandler);
    }
    closeModal("author-modal");
  }

  function applySuggestedTitle() {
    const input = $("title-modal-input");
    const suggestedTitleValue = getSuggestedTitleValue();
    if (input && suggestedTitleValue) {
      input.value = suggestedTitleValue;
      input.focus();
    }
  }

  function toggleEditContent() {
    if (!getPostId()) return;
    setEditMode(!isEditingContent());
  }

  async function applyEdit() {
    try {
      if (!getPostId() || !isEditingContent()) {
        return;
      }
      const editor = $("article-editor");
      const rawContent = editor?.value || "";
      if (!rawContent.trim()) {
        setError("Content cannot be empty.");
        return;
      }
      const result = await applyContentEditAction(getPostId(), rawContent);
      if (!result.ok) {
        if (result.status !== null) {
          setError(result.error || "Failed to apply edit.");
          return;
        }
        setError(result.error || "Error applying edit.");
        return;
      }
      if (result.redirectUrl) {
        window.location = result.redirectUrl;
        return;
      }
      setError("Failed to apply edit.");
    } catch (err) {
      setError(err?.message || "Error applying edit.");
    }
  }

  async function runPolicyEdit() {
    setPolicyEditStatus("editing…");
    setPolicyEditResult("");
    try {
      if (!getPostId()) {
        return;
      }
      const policyText = $("policy-text");
      const policyValue = (policyText?.value || "").trim();
      if (!policyValue) {
        setPolicyEditStatus("Policy text is required.");
        return;
      }
      const result = await runPolicyEditAction(getPostId(), policyValue);
      if (!result.ok) {
        setPolicyEditStatus(result.error || "Edit failed.");
        return;
      }
      if (result.redirectUrl) {
        window.location = result.redirectUrl;
        return;
      }
      window.location.reload();
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
      const result = await suggestTitleAction(content);
      if (!result.ok) {
        setSuggestedTitleValue("");
        setError(result.error || "Failed to suggest title.");
        return;
      }
      const title = (result.data?.suggested_title || "").trim();
      setSuggestedTitleValue(title);
    } catch (err) {
      setSuggestedTitleValue("");
      setError(err?.message || "Failed to suggest title.");
    }
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
    downloadDocumentAction(getMarkdown(), filename)
      .then((result) => {
        if (!result.ok) {
          throw new Error(result.error || "Failed to download document.");
        }
        const blob = result.data;
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename || "article.md";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        setError("");
        closeDownloadModal();
      })
      .catch((err) => {
        setError(err?.message || "Error downloading document.");
      });
  }

  if (!getPostId()) {
    return;
  }
  fetchEditorData(getPostId())
    .then((result) => (result.ok ? result.data : null))
    .then((data) => {
      const target = $("post-revision-indicator");
      if (!target) return;
      const value = data ? data.last_revision_id : undefined;
      if (value === null) {
        target.textContent = "—";
        return;
      }
      if (typeof value === "number") {
        target.textContent = String(value);
        return;
      }
      throw new Error("Invalid last_revision_id");
    })
    .catch(() => {});

  // Initialize markdown rendering from preserved source
  const article = $("article-text");
  const articleSource = $("article-source");
  if (article && articleSource) {
    setMarkdown(articleSource.value || "");
    article.innerHTML = marked.parse(getMarkdown());
  }

  $("open-title-modal-btn")?.addEventListener("click", openTitleModal);
  $("open-author-modal-btn")?.addEventListener("click", openAuthorModal);
  $("title-cancel-btn")?.addEventListener("click", closeTitleModal);
  $("author-cancel-btn")?.addEventListener("click", closeAuthorModal);
  $("apply-suggested-title-btn")?.addEventListener("click", applySuggestedTitle);
  $("set-title-btn")?.addEventListener("click", setTitle);
  $("set-author-btn")?.addEventListener("click", setAuthor);
  $("edit-content-btn")?.addEventListener("click", toggleEditContent);
  $("apply-edit-btn")?.addEventListener("click", applyEdit);
  $("run-policy-edit-btn")?.addEventListener("click", runPolicyEdit);
  $("save-document-btn")?.addEventListener("click", openDownloadModal);
  $("download-cancel-btn")?.addEventListener("click", closeDownloadModal);
  $("download-confirm-btn")?.addEventListener("click", confirmDownload);

}
