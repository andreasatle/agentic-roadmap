export async function setTitle(postId, title) {
  try {
    const resp = await fetch("/blog/set-title", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: postId, title }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      return { ok: false, status: resp.status, error: detail };
    }
    const data = await resp.json();
    return { ok: true, data };
  } catch (err) {
    return { ok: false, status: null, error: err?.message };
  }
}

export async function setAuthor(postId, author) {
  try {
    const resp = await fetch("/blog/set-author", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: postId, author }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      return { ok: false, status: resp.status, error: detail };
    }
    const data = await resp.json();
    return { ok: true, data };
  } catch (err) {
    return { ok: false, status: null, error: err?.message };
  }
}

export async function applyContentEdit(postId, content) {
  try {
    const resp = await fetch("/blog/edit-content", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: postId, content }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      return { ok: false, status: resp.status, error: detail };
    }
    const data = await resp.json();
    return { ok: true, data };
  } catch (err) {
    return { ok: false, status: null, error: err?.message };
  }
}

export async function runPolicyEdit(postId, policyText) {
  try {
    const resp = await fetch("/blog/edit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: postId, policy_text: policyText }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      return { ok: false, status: resp.status, error: detail };
    }
    const data = await resp.json();
    return { ok: true, data };
  } catch (err) {
    return { ok: false, status: null, error: err?.message };
  }
}

export async function suggestTitle(content) {
  try {
    const resp = await fetch("/blog/suggest-title", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      return { ok: false, status: resp.status, error: detail };
    }
    const data = await resp.json();
    return { ok: true, data };
  } catch (err) {
    return { ok: false, status: null, error: err?.message };
  }
}

export async function downloadDocument(markdown, filename) {
  try {
    const resp = await fetch("/document/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markdown, filename }),
    });
    if (!resp.ok) {
      const detail = await resp.text();
      return { ok: false, status: resp.status, error: detail };
    }
    const blob = await resp.blob();
    return { ok: true, data: blob };
  } catch (err) {
    return { ok: false, status: null, error: err?.message };
  }
}

export async function fetchEditorData(postId) {
  try {
    const resp = await fetch(`/blog/editor/data?post_id=${postId}`);
    if (!resp.ok) {
      const detail = await resp.text();
      return { ok: false, status: resp.status, error: detail };
    }
    const data = await resp.json();
    return { ok: true, data };
  } catch (err) {
    return { ok: false, status: null, error: err?.message };
  }
}
