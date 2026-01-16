import { $ } from "./dom.js";
import { initEditorController } from "./editor_controller.js";

let errorArea = null;

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

function initManualEditorPage() {}

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body?.dataset?.page;
  if (!page) return;

  switch (page) {
    case "blog-editor":
      errorArea = $("error-area");
      window.downloadIntentFromForm = downloadIntentFromForm;
      window.openIntentFile = openIntentFile;
      initEditorController();
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

      document.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        if (!target.classList.contains("intent-help")) return;
        const help = target.getAttribute("data-help");
        if (help) {
          showHelp(target, help);
        }
      });
      break;
    case "manual-editor":
      initManualEditorPage();
      break;
  }
});

document.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-href]");
  if (!btn) return;
  window.location.href = btn.dataset.href;
});
