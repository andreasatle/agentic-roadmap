import { $ } from "./dom.js";
import { closeModal, openModal } from "./modals.js";

export function initEditorController() {
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

  const titleModal = $("edit-title-modal");
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
}
