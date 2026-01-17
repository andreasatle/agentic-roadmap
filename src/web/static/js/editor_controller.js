import { $ } from "./dom.js";
import { closeModal, openModal } from "./modals.js";

export function initEditorController() {
  const titleModal = $("edit-title-modal");
  const authorModal = $("edit-author-modal");
  if (!titleModal && !authorModal) {
    return;
  }

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
}
