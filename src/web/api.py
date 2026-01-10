import web.bootstrap
import json
import logging
import os
from io import BytesIO
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yaml
import markdown
from pathlib import Path

from agentic_framework.agent_dispatcher import AgentDispatcherBase
from document_writer.apps.service import generate_document as generate_blog_post
from document_writer.domain.editor.agent import make_editor_agent
from document_writer.domain.editor.api import AgentEditorRequest, AgentEditorResponse
from document_writer.domain.editor.service import edit_document
from document_writer.apps.title_suggester import suggest_title
from apps.blog.edit_service import apply_policy_edit
from apps.blog.storage import (
    TitleAlreadySetError,
    create_post,
    list_posts,
    read_post_meta,
    read_post_content,
    read_post_intent,
    set_post_title,
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



BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"

BLOG_MARKDOWN_EXTENSIONS = ["fenced_code", "tables"]
# No-op policy: editor pipeline runs only to enforce invariants; future policies may replace it.
EDIT_CONTENT_POLICY = "Return the document unchanged."

app = FastAPI()
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)
logger = logging.getLogger(__name__)
editor_agent = make_editor_agent()
editor_dispatcher = AgentDispatcherBase()


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


@app.get("/writer", response_class=HTMLResponse)
def read_writer(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/me")
def read_me(request: Request):
    resume_html = markdown.markdown(
        (BASE_DIR / "content" / "resume.md").read_text(encoding="utf-8"),
        extensions=BLOG_MARKDOWN_EXTENSIONS,
    )
    profile_html = markdown.markdown(
        (BASE_DIR / "content" / "profile.md").read_text(encoding="utf-8"),
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
    ) -> dict[str, str]:
    require_admin(creds)
    intent = payload.intent
    blog_result = generate_blog_post(
        intent=intent,
        trace=False,
    )
    post_id, _ = create_post(
        title=None,
        author=creds.username or "system",
        intent=intent.model_dump(),
        content=blog_result.markdown,
    )
    suggested_title = suggest_title(blog_result.markdown)
    return {
        "post_id": post_id,
        "content": blog_result.markdown,
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


@app.post("/blog/set-title")
def set_blog_title_route(
    payload: TitleSetRequest,
    creds = Depends(security),
) -> dict[str, str]:
    require_admin(creds)
    try:
        meta = set_post_title(payload.post_id, payload.title)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Post not found")
    except TitleAlreadySetError:
        raise HTTPException(status_code=409, detail="Title already set")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"post_id": meta.post_id, "title": meta.title or ""}


@app.post("/blog/edit-content")
def edit_blog_content_route(
    payload: EditContentRequest,
    creds = Depends(security),
) -> dict[str, str]:
    require_admin(creds)
    try:
        intent = read_post_intent(payload.post_id)
        content_path = Path("posts") / payload.post_id / "content.md"
        if not content_path.exists():
            raise FileNotFoundError(f"content.md not found for post {payload.post_id}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Post not found")
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
        raise HTTPException(status_code=400, detail=str(exc))
    content_path.write_text(response.edited_document)
    return {"post_id": payload.post_id, "content": response.edited_document}


@app.post("/blog/edit", response_model=BlogEditResponse)
def edit_blog_post_route(
    payload: BlogEditRequest,
    creds = Depends(security),
) -> BlogEditResponse:
    require_admin(creds)
    try:
        meta = read_post_meta(payload.post_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Post not found")
    if meta.status != "draft":
        raise HTTPException(status_code=409, detail="Post is not draft")
    if payload.policy_text is not None:
        policy_text = payload.policy_text
    else:
        policies_dir = BASE_DIR / "apps" / "blog" / "policies"
        policy_path = policies_dir / f"{payload.policy_id}.txt"
        if not policy_path.exists():
            raise HTTPException(status_code=400, detail="Policy not found")
        policy_text = policy_path.read_text()
    if not policy_text.strip():
        raise HTTPException(status_code=400, detail="Policy text must be non-empty")
    result = apply_policy_edit(payload.post_id, policy_text)
    return result


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
    if include_drafts:
        try:
            creds = await security(request)
            require_admin(creds)
        except HTTPException:
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
    if include_drafts:
        try:
            creds = await security(request)
            require_admin(creds)
        except HTTPException:
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
