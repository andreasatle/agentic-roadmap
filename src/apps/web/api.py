from io import BytesIO

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yaml
from pathlib import Path

from apps.document_writer.service import generate_document
from apps.blog.storage import list_posts
from apps.web.schemas import (
    DocumentGenerateRequest,
    DocumentSaveRequest,
    IntentParseRequest,
    IntentSaveRequest,
)
from domain.intent import load_intent_from_yaml
from dotenv import load_dotenv
load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"

app = FastAPI()
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)


@app.get("/", response_class=HTMLResponse)
def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


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
def generate_document_route(payload: DocumentGenerateRequest) -> dict[str, str]:
    intent = payload.intent
    result = generate_document(
        goal=intent.structural_intent.document_goal,
        audience=intent.structural_intent.audience,
        tone=intent.structural_intent.tone,
        intent=intent,
        trace=False,
    )
    return {"markdown": result.markdown}


@app.post("/document/save")
def save_document(payload: DocumentSaveRequest):
    filename = (payload.filename or "article.md").strip() or "article.md"
    buffer = BytesIO(payload.markdown.encode("utf-8"))
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(buffer, media_type="text/markdown", headers=headers)


@app.get("/blog")
def get_blog_index(include_drafts: bool = False):
    posts = list_posts(include_drafts=include_drafts)
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
