import apps.web.bootstrap
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

from apps.document_writer.service import generate_document
from apps.blog.storage import list_posts, read_post_meta, read_post_content, read_post_intent
from apps.web.schemas import (
    DocumentGenerateRequest,
    DocumentSaveRequest,
    IntentParseRequest,
    IntentSaveRequest,
)
from apps.web.persistence import persist_generation
from apps.web.security import require_admin
from domain.intent import load_intent_from_yaml



BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"

BLOG_MARKDOWN_EXTENSIONS = ["fenced_code", "tables"]

app = FastAPI()
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)
logger = logging.getLogger(__name__)


@app.on_event("startup")
def validate_generated_dir() -> None:
    apps.web.bootstrap.validate_generated_dir()


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


@app.post("/document/generate")
def generate_document_route(
    payload: DocumentGenerateRequest,
    request: Request,
    _: None = Depends(require_admin),
    ) -> dict[str, str]:
    intent = payload.intent
    result = generate_document(
        goal=intent.structural_intent.document_goal,
        audience=intent.structural_intent.audience,
        tone=intent.structural_intent.tone,
        intent=intent,
        trace=False,
    )
    persist_generation(
        intent=intent,
        markdown=result.markdown,
        request_meta={
            "request_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
    )
    return {"markdown": result.markdown}


@app.post("/document/save")
def save_document(payload: DocumentSaveRequest):
    filename = (payload.filename or "article.md").strip() or "article.md"
    buffer = BytesIO(payload.markdown.encode("utf-8"))
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(buffer, media_type="text/markdown", headers=headers)


@app.get("/blog", response_class=HTMLResponse)
def get_blog_index(request: Request, include_drafts: bool = False, format: str = "html"):
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
def get_blog_post(request: Request, post_id: str, include_drafts: bool = False, format: str = "html"):
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