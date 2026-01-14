import argparse
import os
from dotenv import load_dotenv

from document_writer.apps.service import generate_document
from document_writer.domain.intent import load_intent_from_yaml

from apps.blog.edit_service import apply_policy_edit
from apps.blog.post import BlogPost

load_dotenv(override=True)


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
    with open(args.intent, "r", encoding="utf-8") as handle:
        intent = load_intent_from_yaml(handle.read())

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
    with open(args.policy, "r", encoding="utf-8") as handle:
        editing_policy = handle.read()

    result = apply_policy_edit(
        args.post_id,
        editing_policy,
        actor_id=os.path.basename(args.policy),
    )

    for rejected in result.rejected_chunks:
        print(f"Chunk {rejected.chunk_index} rejected: {rejected.reason}")

    if not result.changed_chunks:
        print(f"No changes applied for post: {args.post_id}")
        return
    print(f"Post edited: {args.post_id}")
    print(f"Revision id: {result.revision_id}")
    print(f"Chunks changed: {len(result.changed_chunks)}")


if __name__ == "__main__":
    main()
