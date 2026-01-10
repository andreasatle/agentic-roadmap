import argparse
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

import yaml

from document_writer.apps.service import generate_document
from document_writer.domain.intent import load_intent_from_yaml
from document_writer.domain.editor import edit_document, make_editor_agent, AgentEditorRequest
from document_writer.domain.editor.chunking import Chunk, split_markdown, join_chunks
from document_writer.domain.editor.validation import validate_diff
from agentic_framework.agent_dispatcher import AgentDispatcherBase

from apps.blog.post import BlogPost
from apps.blog.storage import read_post_intent, read_post_meta

load_dotenv(override=True)


POSTS_ROOT = Path("posts")


def main():
    parser = argparse.ArgumentParser(prog="blog")
    sub = parser.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser("generate")
    gen.add_argument("--title", required=True)
    gen.add_argument("--author", required=True)
    gen.add_argument("--intent", required=True)
    gen.add_argument("--status", default="draft")

    edit = sub.add_parser("edit")
    edit.add_argument("--post-id", required=True)
    edit.add_argument("--policy", required=True)

    args = parser.parse_args()

    if args.cmd == "generate":
        generate(args)
    elif args.cmd == "edit":
        edit_post(args)


# ---------- generate ----------

def generate(args):
    intent = load_intent_from_yaml(Path(args.intent).read_text())

    result = generate_document(
        intent=intent,
        trace=False,
    )

    post = BlogPost(
        title=args.title,
        author=args.author,
        intent=intent.model_dump(),
        content=result.markdown,
        status=args.status,
    )

    post_id, path = post.persist()
    print(f"Blog post created: {post_id}")
    print(f"Blog post created at: {path}")


# ---------- edit ----------

def edit_post(args):
    post_dir = POSTS_ROOT / args.post_id
    if not post_dir.exists():
        raise FileNotFoundError(f"Post not found: {post_dir}")

    content_path = post_dir / "content.md"
    meta_path = post_dir / "meta.yaml"
    meta = read_post_meta(args.post_id)
    if meta.status != "draft":
        raise RuntimeError(f"Cannot edit non-draft post: {args.post_id}")

    document = content_path.read_text()
    editing_policy = Path(args.policy).read_text()
    intent = read_post_intent(args.post_id)

    # run editor per chunk
    agent = make_editor_agent()
    dispatcher = AgentDispatcherBase()

    chunks = split_markdown(document)
    original_chunks = chunks
    changed_indices: list[int] = []
    updated_chunks: list[Chunk] = []
    for chunk in chunks:
        response = edit_document(
            AgentEditorRequest(
                document=chunk.text,
                editing_policy=editing_policy,
                intent=intent,
            ),
            dispatcher=dispatcher,
            editor_agent=agent,
        )
        validation = validate_diff(
            before=chunk.text,
            after=response.edited_document,
            policy_text=editing_policy,
        )
        if not validation.accepted:
            print(f"Chunk {chunk.index} rejected: {validation.reason}")
        if validation.accepted and response.edited_document != chunk.text:
            changed_indices.append(chunk.index)
            updated_chunks.append(
                Chunk(
                    index=chunk.index,
                    text=response.edited_document,
                    leading_separator=chunk.leading_separator,
                    trailing_separator=chunk.trailing_separator,
                )
            )
        else:
            updated_chunks.append(chunk)

    if not changed_indices:
        print(f"No changes applied for post: {args.post_id}")
        return

    revisions_dir = post_dir / "revisions"
    revisions_dir.mkdir(exist_ok=True)
    revision_ids: list[int] = []
    for entry in revisions_dir.glob("*.md"):
        stem = entry.stem
        if "_" in stem:
            stem = stem.split("_", 1)[0]
        if stem.isdigit():
            revision_ids.append(int(stem))
    next_rev = max(revision_ids, default=0) + 1

    for chunk in original_chunks:
        if chunk.index in changed_indices:
            snapshot_path = revisions_dir / f"{next_rev}_{chunk.index}.md"
            snapshot_path.write_text(chunk.text)

    assert [c.index for c in updated_chunks] == list(range(len(updated_chunks)))
    updated_document = join_chunks(updated_chunks)
    content_path.write_text(updated_document)

    if meta_path.exists():
        meta_payload = yaml.safe_load(meta_path.read_text()) or {}
        if not isinstance(meta_payload, dict):
            raise ValueError(f"Invalid meta.yaml for post {args.post_id}")
    else:
        meta_payload = {}
    revisions = meta_payload.get("revisions")
    if not isinstance(revisions, list):
        revisions = []
    revisions.append(
        {
            "revision_id": next_rev,
            "policy": str(Path(args.policy).resolve()),
            "changed_chunks": changed_indices,
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
    )
    meta_payload["revisions"] = revisions
    meta_path.write_text(yaml.safe_dump(meta_payload, sort_keys=False, default_flow_style=False))

    print(f"Post edited: {args.post_id}")
    print(f"Revision id: {next_rev}")
    print(f"Chunks changed: {len(changed_indices)}")


if __name__ == "__main__":
    main()
