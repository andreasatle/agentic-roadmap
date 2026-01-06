import argparse
from pathlib import Path

from apps.blog.post import BlogPost
from document_writer.apps.service import generate_document
from document_writer.domain.intent import load_intent_from_yaml
from dotenv import load_dotenv
load_dotenv(override=True)

def main():
    parser = argparse.ArgumentParser(prog="blog")
    sub = parser.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser("generate")
    gen.add_argument("--title", required=True)
    gen.add_argument("--author", required=True)
    gen.add_argument("--intent", required=True)
    gen.add_argument("--status", default="draft")

    args = parser.parse_args()

    if args.cmd == "generate":
        generate(args)


def generate(args):
    intent = load_intent_from_yaml(Path(args.intent).read_text())

    result = generate_document(
        goal=intent.structural_intent.document_goal,
        audience=intent.structural_intent.audience,
        tone=intent.structural_intent.tone,
        intent=intent,
        trace=False,
    )

    intent_dict = intent.model_dump()

    post = BlogPost(
        title=args.title,
        author=args.author,
        intent=intent_dict,
        content=result.markdown,
        status=args.status,
    )

    path = post.persist()
    print(f"Blog post created at: {path}")


if __name__ == "__main__":
    main()
