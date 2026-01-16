import { $ } from "./dom.js";
import {
  applyContentEdit as applyContentEditAction,
  downloadDocument as downloadDocumentAction,
  runPolicyEdit as runPolicyEditAction,
  setAuthor as setAuthorAction,
  setTitle as setTitleAction,
} from "./editor_actions.js";

export function initEditorController() {

  function getPostId() {
    return document.body?.dataset?.postId || null;
  }

  function setError(message) {
    const errorArea = $("error-area");
    if (errorArea) {
      errorArea.textContent = message || "";
    }
  }

  async function setTitle() {
    const input = $("title-modal-input");
    const title = (input?.value || "").trim();
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
      window.location.reload();
    } catch (err) {
      setError(err?.message || "Error setting title.");
    }
  }

  async function setAuthor() {
    const input = $("author-modal-input");
    const author = (input?.value || "").trim();
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
      window.location.reload();
    } catch (err) {
      setError(err?.message || "Error setting author.");
    }
  }

  async function applyEdit() {
    try {
      const editor = $("article-editor");
      const rawContent = editor?.value || "";
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
      window.location.reload();
    } catch (err) {
      setError(err?.message || "Error applying edit.");
    }
  }

  async function runPolicyEdit() {
    try {
      const policyText = $("policy-text");
      const policyValue = (policyText?.value || "").trim();
      const result = await runPolicyEditAction(getPostId(), policyValue);
      if (!result.ok) {
        setError(result.error || "Edit failed.");
        return;
      }
      if (result.redirectUrl) {
        window.location = result.redirectUrl;
        return;
      }
      window.location.reload();
    } catch (err) {
      setError(err?.message || "Edit failed.");
    }
  }

  function confirmDownload() {
    const filenameInput = $("download-filename");
    const filename = (filenameInput?.value || "").trim() || "article.md";
    const markdown = $("article-source")?.value ?? "";
    downloadDocumentAction(markdown, filename)
      .then((result) => {
        if (!result.ok) {
          throw new Error(result.error || "Failed to download document.");
        }
        window.location.reload();
      })
      .catch((err) => {
        setError(err?.message || "Error downloading document.");
      });
  }

  $("set-title-btn")?.addEventListener("click", setTitle);
  $("set-author-btn")?.addEventListener("click", setAuthor);
  $("apply-edit-btn")?.addEventListener("click", applyEdit);
  $("run-policy-edit-btn")?.addEventListener("click", runPolicyEdit);
  $("download-confirm-btn")?.addEventListener("click", confirmDownload);

}
