import { $ } from "./dom.js";
import { closeModal, openModal } from "./modals.js";
import { initHelpPopovers } from "./help_popovers.js";

export function initEditorController() {
  const titleModal = $("edit-title-modal");
  const authorModal = $("edit-author-modal");
  if (!titleModal && !authorModal) {
    return;
  }
  initHelpPopovers(document.body);

  $("open-title-modal-btn")?.addEventListener("click", () =>
    openModal("edit-title-modal", "edit-title-input"),
  );
  $("open-author-modal-btn")?.addEventListener("click", () =>
    openModal("edit-author-modal", "edit-author-input"),
  );
  $("edit-title-cancel-btn")?.addEventListener("click", () =>
    closeModal("edit-title-modal"),
  );
  $("edit-author-cancel-btn")?.addEventListener("click", () =>
    closeModal("edit-author-modal"),
  );

  const titleForm = titleModal?.querySelector("form");
  titleForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const postId = titleForm.querySelector('input[name="post_id"]')?.value ?? "";
    const title = titleForm.querySelector('input[name="title"]')?.value ?? "";
    try {
      const response = await fetch("/blog/set-title", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ post_id: postId, title }),
      });
      if (response.ok) {
        window.location.reload();
        return;
      }
      let message = "Failed to update title.";
      try {
        const payload = await response.json();
        if (payload?.detail) {
          message =
            typeof payload.detail === "string"
              ? payload.detail
              : JSON.stringify(payload.detail);
        }
      } catch {
        const text = await response.text();
        if (text) {
          message = text;
        }
      }
      alert(message);
    } catch (error) {
      alert(error instanceof Error ? error.message : "Failed to update title.");
    }
  });

  const authorForm = authorModal?.querySelector("form");
  authorForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const postId = authorForm.querySelector('input[name="post_id"]')?.value ?? "";
    const author = authorForm.querySelector('input[name="author"]')?.value ?? "";
    try {
      const response = await fetch("/blog/set-author", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ post_id: postId, author }),
      });
      if (response.ok) {
        window.location.reload();
        return;
      }
      let message = "Failed to update author.";
      try {
        const payload = await response.json();
        if (payload?.detail) {
          message =
            typeof payload.detail === "string"
              ? payload.detail
              : JSON.stringify(payload.detail);
        }
      } catch {
        const text = await response.text();
        if (text) {
          message = text;
        }
      }
      alert(message);
    } catch (error) {
      alert(error instanceof Error ? error.message : "Failed to update author.");
    }
  });

  $("open-download-modal-btn")?.addEventListener("click", () =>
    openModal("download-modal", "download-filename"),
  );
  $("download-cancel-btn")?.addEventListener("click", () =>
    closeModal("download-modal"),
  );
  $("download-confirm-btn")?.addEventListener("click", () => {
    const markdown = $("markdown-source")?.value ?? "";
    const filename = $("download-filename")?.value?.trim() || "post.md";
    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    closeModal("download-modal");
  });

  document.querySelectorAll("[data-status-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (button instanceof HTMLButtonElement && button.disabled) {
        return;
      }
      const postId = document.body?.dataset?.postId ?? "";
      const currentStatus = document.body?.dataset?.postStatus ?? "";
      const targetStatus = button.dataset.statusAction ?? "";
      if (!postId || !targetStatus) {
        return;
      }
      if (targetStatus === "archived" && currentStatus === "published") {
        const confirmed = confirm(
          "Archive this post? It will be removed from public view.",
        );
        if (!confirmed) {
          return;
        }
      }
      try {
        const response = await fetch("/blog/status", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ post_id: postId, target_status: targetStatus }),
        });
        if (response.ok) {
          document.body.dataset.postStatus = targetStatus;
          const statusIndicator = document.querySelector(
            ".intent-header-left div",
          );
          if (statusIndicator) {
            statusIndicator.textContent = `Status: ${targetStatus}`;
          }
          document.querySelectorAll("[data-status-action]").forEach((action) => {
            const nextStatus = action.dataset.statusAction ?? "";
            if (action instanceof HTMLButtonElement) {
              action.disabled =
                (nextStatus === "published" && targetStatus !== "draft") ||
                (nextStatus === "archived" && targetStatus !== "published") ||
                (nextStatus === "draft" && targetStatus !== "archived");
            }
          });
          return;
        }
        let message = "Failed to update status.";
        try {
          const payload = await response.json();
          if (payload?.detail) {
            message =
              typeof payload.detail === "string"
                ? payload.detail
                : JSON.stringify(payload.detail);
          }
        } catch {
          const text = await response.text();
          if (text) {
            message = text;
          }
        }
        alert(message);
      } catch (error) {
        alert(error instanceof Error ? error.message : "Failed to update status.");
      }
    });
  });

  initRevisionHistory();
}

async function initRevisionHistory() {
  const statusEl = document.getElementById("revision-history-status");
  const tableEl = document.getElementById("revision-history-table");
  const bodyEl = document.getElementById("revision-history-body");
  const viewerEl = document.getElementById("revision-viewer");
  const viewerBanner = document.getElementById("revision-viewer-banner");
  const viewerContent = document.getElementById("revision-viewer-content");
  const viewerStatus = document.getElementById("revision-viewer-status");
  const viewerCopyBtn = document.getElementById("revision-viewer-copy-btn");
  const viewerReturnBtn = document.getElementById("revision-viewer-return-btn");
  if (!statusEl || !tableEl || !bodyEl) {
    return;
  }
  const postId = document.body?.dataset?.postId ?? "";
  if (!postId) {
    statusEl.textContent = "Missing post id.";
    return;
  }
  statusEl.textContent = "Loading...";
  if (viewerCopyBtn && viewerStatus && viewerEl) {
    viewerCopyBtn.addEventListener("click", async () => {
      const revisionId = Number(viewerEl.dataset.revisionId);
      if (!Number.isFinite(revisionId)) {
        viewerStatus.textContent = "Missing revision id.";
        return;
      }
      await createRevisionFromSource(
        postId,
        revisionId,
        viewerStatus,
        viewerCopyBtn,
      );
    });
  }
  if (viewerReturnBtn) {
    viewerReturnBtn.addEventListener("click", () => {
      window.location.reload();
    });
  }
  try {
    const response = await fetch(
      `/blog/${encodeURIComponent(postId)}/revisions`,
    );
    if (!response.ok) {
      throw new Error("Failed to load revisions.");
    }
    const payload = await response.json();
    if (!Array.isArray(payload)) {
      throw new Error("Invalid revision response.");
    }
    const revisions = payload
      .filter((entry) => entry && typeof entry === "object")
      .map((entry) => ({
        revision_id:
          typeof entry.revision_id === "number"
            ? entry.revision_id
            : Number(entry.revision_id),
        parent_revision_id: entry.parent_revision_id ?? null,
        timestamp: entry.timestamp ?? null,
        delta_type: entry.delta_type ?? null,
        delta_payload: entry.delta_payload ?? null,
      }))
      .filter((entry) => Number.isFinite(entry.revision_id));
    revisions.sort((a, b) => a.revision_id - b.revision_id);
    if (revisions.length === 0) {
      statusEl.textContent = "No revisions yet.";
      tableEl.hidden = true;
      return;
    }
    const headRevisionId = revisions[revisions.length - 1].revision_id;
    bodyEl.innerHTML = "";
    for (const revision of revisions) {
      const row = document.createElement("tr");

      const idCell = document.createElement("td");
      idCell.textContent = `r${revision.revision_id}`;
      if (revision.revision_id === headRevisionId) {
        const badge = document.createElement("span");
        badge.className = "revision-badge";
        badge.textContent = "Head";
        idCell.appendChild(badge);
      }
      row.appendChild(idCell);

      const tsCell = document.createElement("td");
      tsCell.textContent = revision.timestamp ?? "—";
      row.appendChild(tsCell);

      const typeCell = document.createElement("td");
      const displayType = formatDeltaType(revision.delta_type);
      typeCell.textContent = displayType;
      if (
        revision.delta_type &&
        typeof revision.delta_type === "string" &&
        displayType !== revision.delta_type
      ) {
        typeCell.title = revision.delta_type;
      }
      row.appendChild(typeCell);

      const noteCell = document.createElement("td");
      const note = deriveRevisionNote(revision);
      noteCell.textContent = note || "—";
      row.appendChild(noteCell);

      const actionCell = document.createElement("td");
      if (revision.revision_id !== headRevisionId) {
        const viewButton = document.createElement("button");
        viewButton.type = "button";
        viewButton.className = "btn btn--ghost revision-action-btn";
        viewButton.textContent = "View";
        viewButton.addEventListener("click", async () => {
          if (
            !viewerEl ||
            !viewerBanner ||
            !viewerContent ||
            !viewerStatus ||
            !viewerCopyBtn ||
            !viewerReturnBtn
          ) {
            return;
          }
          document.body?.classList.add("history-mode");
          viewerBanner.textContent = `Viewing revision r${revision.revision_id} (read-only)`;
          viewerContent.textContent = "";
          viewerStatus.textContent = "Loading revision...";
          try {
            const response = await fetch(
              `/blog/${encodeURIComponent(postId)}/revisions/${revision.revision_id}`,
            );
            if (!response.ok) {
              let message = "Failed to load revision.";
              try {
                const payload = await response.json();
                if (payload?.detail) {
                  message =
                    typeof payload.detail === "string"
                      ? payload.detail
                      : JSON.stringify(payload.detail);
                }
              } catch {
                const text = await response.text();
                if (text) {
                  message = text;
                }
              }
              throw new Error(message);
            }
            const payload = await response.json();
            viewerContent.textContent =
              typeof payload.content === "string" ? payload.content : "";
            viewerEl.dataset.revisionId = String(revision.revision_id);
            viewerStatus.textContent = "";
          } catch (error) {
            viewerStatus.textContent =
              error instanceof Error
                ? error.message
                : "Failed to load revision.";
          }
        });
        actionCell.appendChild(viewButton);

        const copyButton = document.createElement("button");
        copyButton.type = "button";
        copyButton.className = "btn btn--ghost revision-action-btn";
        copyButton.textContent = "Create new revision from this";
        copyButton.addEventListener("click", async () => {
          await createRevisionFromSource(
            postId,
            revision.revision_id,
            statusEl,
            copyButton,
          );
        });
        actionCell.appendChild(copyButton);
      }
      row.appendChild(actionCell);

      bodyEl.appendChild(row);
    }
    statusEl.textContent = "";
    tableEl.hidden = false;
  } catch (error) {
    tableEl.hidden = true;
    statusEl.textContent =
      error instanceof Error ? error.message : "Failed to load revisions.";
  }
}

function formatDeltaType(deltaType) {
  if (!deltaType || typeof deltaType !== "string") {
    return "—";
  }
  const normalized = deltaType.toLowerCase();
  if (normalized.includes("revert")) {
    return "revert";
  }
  if (normalized.includes("create")) {
    return "create";
  }
  if (normalized.includes("content") || normalized.includes("edit")) {
    return "edit";
  }
  return deltaType;
}

function deriveRevisionNote(revision) {
  if (!revision || typeof revision !== "object") {
    return "";
  }
  const deltaType = revision.delta_type;
  if (!deltaType || typeof deltaType !== "string") {
    return "";
  }
  const normalized = deltaType.toLowerCase();
  if (!normalized.includes("revert")) {
    return "";
  }
  const payload = revision.delta_payload;
  if (!payload || typeof payload !== "object") {
    return "revert";
  }
  const target =
    payload.reverted_to_revision_id ??
    payload.target_revision_id ??
    payload.revision_id;
  if (typeof target === "number" && Number.isFinite(target)) {
    return `revert -> r${target}`;
  }
  if (typeof target === "string" && target.trim()) {
    return `revert -> r${target}`;
  }
  return "revert";
}

async function createRevisionFromSource(
  postId,
  revisionId,
  statusEl,
  buttonEl,
) {
  if (buttonEl) {
    buttonEl.disabled = true;
  }
  statusEl.textContent = "Creating new revision...";
  try {
    const response = await fetch(
      `/blog/${encodeURIComponent(postId)}/revisions/${revisionId}/copy`,
      { method: "POST" },
    );
    if (!response.ok) {
      let message = "Failed to create revision.";
      try {
        const payload = await response.json();
        if (payload?.detail) {
          message =
            typeof payload.detail === "string"
              ? payload.detail
              : JSON.stringify(payload.detail);
        }
      } catch {
        const text = await response.text();
        if (text) {
          message = text;
        }
      }
      throw new Error(message);
    }
    window.location.reload();
  } catch (error) {
    statusEl.textContent =
      error instanceof Error ? error.message : "Failed to create revision.";
    if (buttonEl) {
      buttonEl.disabled = false;
    }
  }
}
