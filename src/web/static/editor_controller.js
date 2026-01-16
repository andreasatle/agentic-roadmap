import { $ } from "./dom.js";
import {
  getCurrentMarkdown,
  getCurrentPostId,
  getIsEditingContent,
  getSuggestedTitleValue,
  setCurrentMarkdown,
  setCurrentPostId,
  setIsEditingContent,
  setSuggestedTitleValue as setSuggestedTitleValueState,
} from "./editor_state.js";
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
  const errorArea = $("error-area");

  function setError(message) {
    if (errorArea) {
      errorArea.textContent = message || "";
    }
  }

  function setSuggestedTitleValue(title) {
    setSuggestedTitleValueState(title);
    const target = $("suggested-title-text");
    const wrap = $("suggested-title-wrap");
    if (target) {
      const suggestedTitleValue = getSuggestedTitleValue();
      target.textContent = suggestedTitleValue ? `Suggested: "${suggestedTitleValue}"` : "";
    }
    if (wrap) {
      wrap.hidden = !getSuggestedTitleValue();
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
    setIsEditingContent(enabled);
    const editor = $("article-editor");
    const editBtn = $("edit-content-btn");
    if (editor) {
      if (enabled) editor.value = getCurrentMarkdown() || "";
    }
    if (editBtn) editBtn.textContent = enabled ? "Cancel edit" : "Edit content";
  }

  async function setTitle() {
    if (!getCurrentPostId()) {
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
      const result = await setTitleAction(getCurrentPostId(), title);
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
    if (!getCurrentPostId()) {
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
      const result = await setAuthorAction(getCurrentPostId(), author);
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
    const source = getIsEditingContent() && editor ? editor.value : getCurrentMarkdown();
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
    if (!getCurrentPostId()) return;
    setEditMode(!getIsEditingContent());
  }

  async function applyEdit() {
    try {
      if (!getCurrentPostId() || !getIsEditingContent()) {
        return;
      }
      const editor = $("article-editor");
      const rawContent = editor?.value || "";
      if (!rawContent.trim()) {
        setError("Content cannot be empty.");
        return;
      }
      const result = await applyContentEditAction(getCurrentPostId(), rawContent);
      if (!result.ok) {
        if (result.status !== null) {
          setError(result.error || "Failed to apply edit.");
          return;
        }
        setError(result.error || "Error applying edit.");
        return;
      }
      setCurrentMarkdown(result.data.content || "");
      const articleArea = $("article-text");
      if (articleArea) {
        articleArea.innerHTML = marked.parse(getCurrentMarkdown());
      }
      setSuggestedTitleValue("");
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
      if (!getCurrentPostId()) {
        return;
      }
      const policyText = $("policy-text");
      const policyValue = (policyText?.value || "").trim();
      if (!policyValue) {
        setPolicyEditStatus("Policy text is required.");
        return;
      }
      const result = await runPolicyEditAction(getCurrentPostId(), policyValue);
      if (!result.ok) {
        setPolicyEditStatus(result.error || "Edit failed.");
        return;
      }
      const data = result.data;
      setCurrentMarkdown(data.content || "");
      const articleArea = $("article-text");
      if (articleArea) {
        articleArea.innerHTML = marked.parse(getCurrentMarkdown());
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
    downloadDocumentAction(getCurrentMarkdown(), filename)
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

  const postId = document.body?.dataset?.postId;
  if (!postId) {
    return;
  }
  setCurrentPostId(postId);
  fetchEditorData(getCurrentPostId())
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
    setCurrentMarkdown(articleSource.value || "");
    article.innerHTML = marked.parse(getCurrentMarkdown());
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
