import { initEditorController } from "./editor_controller.js";

function initManualEditorPage() {}

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body?.dataset?.page;
  if (!page) return;

  switch (page) {
    case "blog-editor":
      initEditorController();
      break;
    case "manual-editor":
      initManualEditorPage();
      break;
  }
});
