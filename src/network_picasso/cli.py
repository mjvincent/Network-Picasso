from __future__ import annotations

import argparse
import json
from pathlib import Path

from .drawio import render_drawio
from .intake import build_architecture_from_inputs
from .questions import find_design_gaps


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def generate(args: argparse.Namespace) -> None:
    architecture = _load_json(args.input)
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_drawio(architecture, diagram_type=args.type), encoding="utf-8")
    print(f"Wrote {output}")


def ask(args: argparse.Namespace) -> None:
    architecture = _load_json(args.input)
    gaps = find_design_gaps(architecture)
    if not gaps:
        print("No obvious design gaps found.")
        return

    for index, gap in enumerate(gaps, start=1):
        print(f"{index}. [{gap['area']}] {gap['question']}")


def intake(args: argparse.Namespace) -> None:
    architecture = build_architecture_from_inputs(args.input, project_name=args.project_name)
    gaps = find_design_gaps(architecture)
    architecture["questions"]["open"] = [gap["question"] for gap in gaps]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(architecture, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"Sources: {len(architecture.get('sources', []))}")
    print(f"Open questions: {len(gaps)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="network-picasso",
        description="Generate and review IBM Cloud architecture diagrams locally.",
    )
    subparsers = parser.add_subparsers(required=True)

    generate_parser = subparsers.add_parser("generate", help="Generate a Draw.io file.")
    generate_parser.add_argument("input", type=Path, help="Architecture JSON input.")
    generate_parser.add_argument("--output", "-o", type=Path, required=True, help="Output .drawio path.")
    generate_parser.add_argument(
        "--type",
        choices=["context", "logical", "deployment"],
        default="deployment",
        help="Diagram type to render.",
    )
    generate_parser.set_defaults(func=generate)

    ask_parser = subparsers.add_parser("ask", help="List pointed design questions for missing details.")
    ask_parser.add_argument("input", type=Path, help="Architecture JSON input.")
    ask_parser.set_defaults(func=ask)

    intake_parser = subparsers.add_parser("intake", help="Extract a first-pass architecture JSON from input files.")
    intake_parser.add_argument("input", type=Path, help="Input file or directory.")
    intake_parser.add_argument("--output", "-o", type=Path, required=True, help="Output architecture JSON path.")
    intake_parser.add_argument("--project-name", help="Override inferred project name.")
    intake_parser.set_defaults(func=intake)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
