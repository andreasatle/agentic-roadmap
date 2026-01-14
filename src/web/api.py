import web.bootstrap
import hashlib
import json
import logging
import os
from io import BytesIO
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yaml
import markdown
from pydantic import BaseModel

from agentic_framework.agent_dispatcher import AgentDispatcherBase
from document_writer.apps.service import generate_document as generate_blog_post
from document_writer.domain.editor.agent import make_editor_agent
from document_writer.domain.editor.api import AgentEditorRequest, AgentEditorResponse
from document_writer.domain.editor.service import edit_document
from document_writer.domain.editor.chunking import split_markdown
from document_writer.apps.title_suggester import suggest_title
from apps.blog.edit_service import apply_policy_edit
from apps.blog.post_revision_writer import PostRevisionWriter
from apps.blog.storage import (
    create_post,
    list_posts,
    read_post_meta,
    read_post_content,
    read_post_intent,
    write_post_content,
    write_revision_snapshots,
    read_revision_metadata,
)
from web.schemas import (
    DocumentGenerateRequest,
    DocumentSaveRequest,
    EditContentRequest,
    BlogEditRequest,
    BlogEditResponse,
    IntentParseRequest,
    IntentSaveRequest,
    TitleSetRequest,
    TitleSuggestRequest,
)
from web.security import require_admin, security
from document_writer.domain.intent import load_intent_from_yaml
from document_writer.domain.intent.types import IntentEnvelope



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

BLOG_MARKDOWN_EXTENSIONS = ["fenced_code", "tables"]
# No-op policy: editor pipeline runs only to enforce invariants; future policies may replace it.
EDIT_CONTENT_POLICY = "Return the document unchanged."

app = FastAPI()
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)
logger = logging.getLogger(__name__)
editor_agent = make_editor_agent()
editor_dispatcher = AgentDispatcherBase()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _changed_chunk_indices(before: str, after: str) -> list[int]:
    before_chunks = split_markdown(before)
    after_chunks = split_markdown(after)
    max_len = max(len(before_chunks), len(after_chunks))
    changed: list[int] = []
    for index in range(max_len):
        before_text = before_chunks[index].text if index < len(before_chunks) else None
        after_text = after_chunks[index].text if index < len(after_chunks) else None
        if before_text != after_text:
            changed.append(index)
    return changed


class AuthorSetRequest(BaseModel):
    post_id: str
    author: str


@app.on_event("startup")
def validate_generated_dir() -> None:
    web.bootstrap.validate_generated_dir()


@app.get("/admin/generations")
def list_generations(
    request: Request,
    limit: int = 50,
    _: None = Depends(require_admin),
) -> list[dict[str, str | None]]:
    capped = min(max(limit, 0), 500)
    index_path = os.path.join(
        os.environ.get("AGENTIC_GENERATED_DIR") or "/opt/agentic/data/generated",
        "index.jsonl",
    )
    if not os.path.exists(index_path):
        return []
    entries: list[dict[str, str | None]] = []
    try:
        with open(index_path, "r", encoding="utf-8") as handle:
            for line in handle:
                payload = line.strip()
                if not payload:
                    continue
                try:
                    item = json.loads(payload)
                except json.JSONDecodeError:
                    logger.exception("Malformed generation index line")
                    continue
                if isinstance(item, dict):
                    entries.append(item)
                else:
                    logger.exception("Malformed generation index entry")
    except Exception:
        logger.exception("Failed to read generation index")
        return []
    entries.reverse()
    if capped == 0:
        return []
    return entries[:capped]


@app.get("/", response_class=HTMLResponse)
def read_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/blog/editor")
def read_editor_entry(
    request: Request,
    post_id: str | None = None,
    mode: str | None = None,
    creds = Depends(security),
):
    require_admin(creds)
    if mode not in {"entry", "create", "edit", None}:
        logger.warning(f"Invalid editor mode '{mode}', defaulting to entry")
        mode = "entry"
    accept = request.headers.get("accept", "")
    if "application/json" in accept.lower():
        raise HTTPException(status_code=406, detail="Editor renders HTML only")
    posts = list_posts(include_drafts=True)
    draft_posts = [post for post in posts if post.status == "draft"]
    payload: dict[str, object] = {
        "request": request,
        "draft_posts": draft_posts,
    }
    if post_id:
        try:
            meta = read_post_meta(post_id)
            content = read_post_content(post_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Post not found")
        try:
            intent = read_post_intent(post_id)
        except FileNotFoundError:
            intent = {}
        payload.update(
            {
                "post_id": post_id,
                "mode": "edit",
                "meta": meta,
                "content": content,
                "intent": intent,
            },
        )
        return templates.TemplateResponse("blog_editor.html", payload)
    if mode == "create":
        payload["mode"] = "create"
    else:
        payload["mode"] = "entry"
    return templates.TemplateResponse("blog_editor.html", payload)


@app.get("/blog/editor/data")
def read_editor_data(
    post_id: str,
    creds = Depends(security),
) -> dict[str, object]:
    require_admin(creds)
    try:
        meta = read_post_meta(post_id)
        content = read_post_content(post_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Post not found")
    try:
        intent = read_post_intent(post_id)
    except FileNotFoundError:
        intent = {}
    revisions = read_revision_metadata(post_id)
    if not isinstance(revisions, list):
        raise HTTPException(status_code=500, detail="Invalid revision metadata")
    last_revision_id = None
    if revisions:
        revision_ids: list[int] = []
        for entry in revisions:
            if not isinstance(entry, dict):
                raise HTTPException(status_code=500, detail="Invalid revision metadata")
            revision_id = entry.get("revision_id")
            if not isinstance(revision_id, int):
                raise HTTPException(status_code=500, detail="Invalid revision metadata")
            revision_ids.append(revision_id)
        last_revision_id = max(revision_ids) if revision_ids else None
    meta_payload = meta.model_dump() if hasattr(meta, "model_dump") else meta
    return {
        "post_id": post_id,
        "content": content,
        "intent": intent,
        "meta": meta_payload,
        "status": meta.status,
        "last_revision_id": last_revision_id,
        "revisions": revisions,
    }


@app.get("/blog/writer")
def redirect_writer():
    return RedirectResponse("/blog/editor", status_code=307)


@app.get("/me")
def read_me(request: Request):
    resume_html = markdown.markdown(
        open(os.path.join(BASE_DIR, "content", "resume.md"), "r", encoding="utf-8").read(),
        extensions=BLOG_MARKDOWN_EXTENSIONS,
    )
    profile_html = markdown.markdown(
        open(os.path.join(BASE_DIR, "content", "profile.md"), "r", encoding="utf-8").read(),
        extensions=BLOG_MARKDOWN_EXTENSIONS,
    )

    return templates.TemplateResponse(
        "me.html",
        {
            "request": request,
            "resume_html": resume_html,
            "profile_html": profile_html,
        },
    )


@app.post("/intent/parse")
def parse_intent(payload: IntentParseRequest):
    try:
        intent = load_intent_from_yaml(payload.yaml_text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return intent.model_dump()


@app.post("/intent/save")
def save_intent(payload: IntentSaveRequest):
    filename = (payload.filename or "intent.yaml").strip() or "intent.yaml"
    yaml_text = yaml.safe_dump(payload.intent.model_dump(), sort_keys=False, default_flow_style=False)
    buffer = BytesIO(yaml_text.encode("utf-8"))
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(buffer, media_type="text/yaml", headers=headers)


@app.post("/blog/generate")
def generate_blog_post_route(
    payload: DocumentGenerateRequest,
    creds = Depends(security),
    ) -> dict[str, str | None]:
    require_admin(creds)
    intent = payload.intent
    author = (creds.username or "").strip()
    if not author:
        raise HTTPException(status_code=400, detail="Author must be set via /blog/set-author")
    # content-only authority: writer generates content, metadata remains blog-owned
    post_id, _ = create_post(
        title=None,
        author=author,
        intent=intent.model_dump(),
        content="",
    )
    blog_result = generate_blog_post(
        intent=intent,
        trace=False,
    )
    markdown = blog_result.markdown
    before_content = read_post_content(post_id)
    before_hash = _hash_text(before_content)
    after_hash = _hash_text(markdown)
    snapshot_chunks = [
        {"index": chunk.index, "text": chunk.text}
        for chunk in split_markdown(markdown)
    ]
    writer = PostRevisionWriter()
    revision_id = writer.apply_delta(
        post_id,
        actor={"type": "generator", "id": author},
        delta_type="content_free_edit",
        delta_payload={
            "changed_chunks": _changed_chunk_indices(before_content, markdown),
            "before_hash": before_hash,
            "after_hash": after_hash,
        },
    )
    revision_recorded = True
    if not isinstance(revision_id, int):
        raise HTTPException(status_code=500, detail="Failed to record revision")
    write_revision_snapshots(post_id, revision_id, snapshot_chunks)
    if not revision_recorded:
        raise HTTPException(status_code=500, detail="Revision required before content write")
    write_post_content(post_id, markdown)
    suggested_title = None
    if isinstance(markdown, str) and markdown.strip():
        suggested_title = suggest_title(markdown)
    return {
        "post_id": post_id,
        "content": markdown,
        "suggested_title": suggested_title,
    }


@app.post("/blog/suggest-title")
def suggest_blog_title_route(
    payload: TitleSuggestRequest,
    creds = Depends(security),
) -> dict[str, str]:
    require_admin(creds)
    title = suggest_title(payload.content)
    return {"suggested_title": title}


@app.post("/blog/create")
async def create_blog_post_route(
    request: Request,
    creds = Depends(security),
) -> RedirectResponse:
    require_admin(creds)
    form = await request.form()
    intent_text = form.get("intent")
    if not isinstance(intent_text, str) or not intent_text:
        raise HTTPException(status_code=400, detail="Invalid intent payload")
    try:
        intent_payload = json.loads(intent_text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid intent payload")
    if not isinstance(intent_payload, dict):
        raise HTTPException(status_code=400, detail="Invalid intent payload")
    try:
        intent = IntentEnvelope.model_validate(intent_payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    post_id, _ = create_post(
        title=None,
        author=(creds.username or "unknown"),
        intent=intent_payload,
        content="",
    )
    blog_result = generate_blog_post(
        intent=intent,
        trace=False,
    )
    markdown = blog_result.markdown
    before_content = read_post_content(post_id)
    before_hash = _hash_text(before_content)
    after_hash = _hash_text(markdown)
    snapshot_chunks = [
        {"index": chunk.index, "text": chunk.text}
        for chunk in split_markdown(markdown)
    ]
    writer = PostRevisionWriter()
    revision_id = writer.apply_delta(
        post_id,
        actor={"type": "generator", "id": creds.username or "editor"},
        delta_type="content_free_edit",
        delta_payload={
            "changed_chunks": _changed_chunk_indices(before_content, markdown),
            "before_hash": before_hash,
            "after_hash": after_hash,
        },
    )
    revision_recorded = True
    if not isinstance(revision_id, int):
        raise HTTPException(status_code=500, detail="Failed to record revision")
    write_revision_snapshots(post_id, revision_id, snapshot_chunks)
    if not revision_recorded:
        raise HTTPException(status_code=500, detail="Revision required before content write")
    write_post_content(post_id, markdown)
    return RedirectResponse(f"/blog/editor?post_id={post_id}", status_code=303)


@app.post("/blog/set-title")
def set_blog_title_route(
    payload: TitleSetRequest,
    creds = Depends(security),
) -> dict[str, str]:
    require_admin(creds)
    # UI state is non-authoritative; metadata mutations are revision-led only.
    try:
        read_post_meta(payload.post_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Post not found")
    writer = PostRevisionWriter()
    new_title = (payload.title or "").strip()
    if not new_title:
        reason = "Title must be a non-empty string"
        writer.apply_delta(
            payload.post_id,
            actor={"type": "human", "id": creds.username or "editor"},
            delta_type="title_changed",
            delta_payload={"new_title": new_title},
            reason=reason,
            status="rejected",
        )
        raise HTTPException(status_code=400, detail={"rejection_reason": reason})
    writer.apply_delta(
        payload.post_id,
        actor={"type": "human", "id": creds.username or "editor"},
        delta_type="title_changed",
        delta_payload={"new_title": new_title},
    )
    return {"post_id": payload.post_id, "title": new_title}


@app.post("/blog/set-author")
def set_blog_author_route(
    payload: AuthorSetRequest,
    creds = Depends(security),
) -> dict[str, str]:
    require_admin(creds)
    # UI state is non-authoritative; metadata mutations are revision-led only.
    try:
        read_post_meta(payload.post_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Post not found")
    writer = PostRevisionWriter()
    writer.apply_delta(
        payload.post_id,
        actor={"type": "human", "id": creds.username or "editor"},
        delta_type="author_changed",
        delta_payload={"new_author": payload.author},
    )
    return {"post_id": payload.post_id, "author": payload.author}


@app.post("/blog/edit-content")
def edit_blog_content_route(
    payload: EditContentRequest,
    creds = Depends(security),
) -> dict[str, str]:
    require_admin(creds)
    # UI state is non-authoritative; content mutations are revision-led only.
    try:
        before_content = read_post_content(payload.post_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Post not found")
    try:
        intent = read_post_intent(payload.post_id)
    except FileNotFoundError:
        intent = {}
    writer = PostRevisionWriter()
    before_hash = _hash_text(before_content)
    try:
        response = edit_document(
            AgentEditorRequest(
                document=payload.content,
                editing_policy=EDIT_CONTENT_POLICY,
                intent=intent,
            ),
            dispatcher=editor_dispatcher,
            editor_agent=editor_agent,
        )
    except ValueError as exc:
        writer.apply_delta(
            payload.post_id,
            actor={"type": "human", "id": creds.username or "editor"},
            delta_type="content_free_edit",
            delta_payload={
                "changed_chunks": _changed_chunk_indices(before_content, payload.content),
                "before_hash": before_hash,
                "after_hash": _hash_text(payload.content),
            },
            reason=str(exc),
            status="rejected",
        )
        raise HTTPException(status_code=400, detail={"rejection_reason": str(exc)})
    except Exception as exc:
        writer.apply_delta(
            payload.post_id,
            actor={"type": "human", "id": creds.username or "editor"},
            delta_type="content_free_edit",
            delta_payload={
                "changed_chunks": _changed_chunk_indices(before_content, payload.content),
                "before_hash": before_hash,
                "after_hash": _hash_text(payload.content),
            },
            reason=str(exc),
            status="rejected",
        )
        raise HTTPException(status_code=500, detail="Edit failed")
    if response.edited_document == before_content:
        writer.apply_delta(
            payload.post_id,
            actor={"type": "human", "id": creds.username or "editor"},
            delta_type="content_free_edit",
            delta_payload={
                "changed_chunks": [],
                "before_hash": before_hash,
                "after_hash": before_hash,
            },
            reason="No content changes",
            status="rejected",
        )
        return {
            "post_id": payload.post_id,
            "content": response.edited_document,
            "rejection_reason": "No content changes",
        }
    snapshot_chunks = [
        {"index": chunk.index, "text": chunk.text}
        for chunk in split_markdown(response.edited_document)
    ]
    revision_id = writer.apply_delta(
        payload.post_id,
        actor={"type": "human", "id": creds.username or "editor"},
        delta_type="content_free_edit",
        delta_payload={
            "changed_chunks": _changed_chunk_indices(before_content, response.edited_document),
            "before_hash": before_hash,
            "after_hash": _hash_text(response.edited_document),
        },
    )
    revision_recorded = True
    if not isinstance(revision_id, int):
        raise HTTPException(status_code=500, detail="Failed to record revision")
    write_revision_snapshots(payload.post_id, revision_id, snapshot_chunks)
    if not revision_recorded:
        raise HTTPException(status_code=500, detail="Revision required before content write")
    write_post_content(payload.post_id, response.edited_document)
    return {"post_id": payload.post_id, "content": response.edited_document}


@app.post("/blog/edit", response_model=BlogEditResponse)
def edit_blog_post_route(
    payload: BlogEditRequest,
    creds = Depends(security),
) -> BlogEditResponse:
    require_admin(creds)
    # UI state is non-authoritative; policy edits are revision-led only.
    try:
        meta = read_post_meta(payload.post_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Post not found")
    if meta.status != "draft":
        raise HTTPException(status_code=409, detail="Post is not draft")
    if payload.policy_text is not None:
        policy_text = payload.policy_text
    else:
        policies_dir = os.path.join(BASE_DIR, "apps", "blog", "policies")
        policy_path = os.path.join(policies_dir, f"{payload.policy_id}.txt")
        if not os.path.exists(policy_path):
            raise HTTPException(status_code=400, detail="Policy not found")
        with open(policy_path, "r", encoding="utf-8") as handle:
            policy_text = handle.read()
    if not policy_text.strip():
        raise HTTPException(status_code=400, detail="Policy text must be non-empty")
    result = apply_policy_edit(
        payload.post_id,
        policy_text,
        actor_id=payload.policy_id or "inline",
    )
    return result


@app.get("/blog/revisions")
def list_blog_revisions(
    post_id: str,
    creds = Depends(security),
) -> list[dict[str, object]]:
    require_admin(creds)
    try:
        read_post_meta(post_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Post not found")
    revisions = read_revision_metadata(post_id)
    if not isinstance(revisions, list):
        raise HTTPException(status_code=500, detail="Invalid revisions")
    summaries: list[dict[str, object]] = []
    for entry in revisions:
        if not isinstance(entry, dict):
            raise HTTPException(status_code=500, detail="Invalid revision entry")
        summary: dict[str, object] = {
            "revision_id": entry.get("revision_id"),
            "actor": entry.get("actor"),
            "delta_type": entry.get("delta_type"),
            "status": entry.get("status"),
        }
        if "reason" in entry:
            summary["reason"] = entry.get("reason")
        summaries.append(summary)
    summaries.sort(key=lambda item: item.get("revision_id") or 0)
    return summaries


@app.post("/document/save")
def save_document(payload: DocumentSaveRequest):
    filename = (payload.filename or "article.md").strip() or "article.md"
    buffer = BytesIO(payload.markdown.encode("utf-8"))
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(buffer, media_type="text/markdown", headers=headers)


@app.post("/agent-editor/edit")
def edit_document_route(
    payload: AgentEditorRequest,
    _: None = Depends(require_admin),
) -> AgentEditorResponse:
    logger.info("agent-editor request received")
    try:
        logger.info("agent-editor controller invoked")
        response = edit_document(
            payload,
            dispatcher=editor_dispatcher,
            editor_agent=editor_agent,
        )
        logger.info("agent-editor request succeeded")
        return response
    except Exception:
        logger.info("agent-editor request failed")
        raise


@app.get("/blog", response_class=HTMLResponse)
async def get_blog_index(request: Request, include_drafts: bool = False, format: str = "html"):
    include_drafts = False
    posts = list_posts(include_drafts=include_drafts)
    if format == "html":
        return templates.TemplateResponse(
            "blog_index.html",
            {"request": request, "posts": posts, "include_drafts": include_drafts},
        )
    result = [
        {
            "post_id": p.post_id,
            "title": p.title,
            "author": p.author,
            "created_at": p.created_at,
        }
        for p in posts
    ]
    return result


@app.get("/blog/{post_id}", response_class=HTMLResponse)
async def get_blog_post(request: Request, post_id: str, include_drafts: bool = False, format: str = "html"):
    include_drafts = False
    try:
        meta = read_post_meta(post_id)
        if not include_drafts and meta.status != "published":
            raise HTTPException(status_code=404, detail="Post not found")
        content = read_post_content(post_id)
        intent = read_post_intent(post_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Post not found")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if format == "html":
        content_html = markdown.markdown(
            content,
            extensions=BLOG_MARKDOWN_EXTENSIONS,
        )
        return templates.TemplateResponse(
            "blog_post.html",
            {
                "request": request,
                "meta": meta,
                "content_html": content_html,
                "intent": intent,
                "include_drafts": include_drafts,
            },
        )

    return {
        "post_id": meta.post_id,
        "title": meta.title,
        "author": meta.author,
        "created_at": meta.created_at,
        "status": meta.status,
        "content": content,
        "intent": intent,
    }

@app.get("/architecture", response_class=HTMLResponse)
def read_architecture(request: Request):
    return templates.TemplateResponse(
        "architecture.html",
        {"request": request},
    )

@app.get("/architecture/authority", response_class=HTMLResponse)
def read_authority(request: Request):
    return templates.TemplateResponse(
        "authority.html",
        {"request": request},
    )

@app.get("/architecture/trace", response_class=HTMLResponse)
def read_trace(request: Request):
    return templates.TemplateResponse(
        "trace.html",
        {"request": request},
    )

@app.get("/architecture/dogma", response_class=HTMLResponse)
def read_dogma(request: Request):
    return templates.TemplateResponse(
        "dogma.html",
        {"request": request},
    )
