#!/usr/bin/env python3
"""Build the VRX Physics Laboratory publication artifacts from canonical Markdown.

Canonical source files are listed in ../book-manifest.json. Generated outputs must not
be hand-edited. The research edition preserves equations and technical Markdown. The
ElevenReader edition applies narration-oriented normalization while preserving the
substantive spoken explanations written into the canonical chapters.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

BOOK_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = BOOK_ROOT / "book-manifest.json"

GENERATED_NOTICE = (
    "<!-- GENERATED FILE. DO NOT HAND EDIT. "
    "Edit canonical files listed in book-manifest.json and rebuild. -->\n\n"
)


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def read_source(relative_path: str) -> str:
    return (BOOK_ROOT / relative_path).read_text(encoding="utf-8").strip() + "\n"


def source_sequence(manifest: dict, *, include_research_appendices: bool) -> list[str]:
    source = manifest["canonical_source"]
    items = [source["front_matter"], *source["chapters"], *source["back_matter"]]
    if include_research_appendices:
        items.extend(source.get("research_appendices", []))
    return items


def assemble_research(manifest: dict) -> str:
    pieces = [GENERATED_NOTICE.rstrip()]
    for relative in source_sequence(manifest, include_research_appendices=True):
        pieces.append(read_source(relative).rstrip())
    return "\n\n<!-- ============================================================ -->\n\n".join(pieces).strip() + "\n"


def strip_display_math(text: str) -> str:
    """Remove display-only math blocks from the narration edition.

    Canonical chapters are required to explain each important equation in prose before
    or after the display. Removing the visual block prevents a speech engine from
    reading raw LaTeX syntax as though it were the lesson itself.
    """
    lines = text.splitlines()
    out: list[str] = []
    in_math = False
    end_token = None

    for line in lines:
        stripped = line.strip()
        if not in_math and stripped in {"\\[", "$$"}:
            in_math = True
            end_token = "\\]" if stripped == "\\[" else "$$"
            continue
        if in_math:
            if stripped == end_token:
                in_math = False
                end_token = None
            continue
        out.append(line)
    return "\n".join(out)


def normalize_tables(text: str) -> str:
    """Convert Markdown table rows into speech-friendly sentences."""
    output: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if cells and all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
                continue
            cells = [c for c in cells if c]
            if cells:
                output.append("; ".join(cells) + ".")
            continue
        output.append(line)
    return "\n".join(output)


def remove_markdown_links(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\((?:https?://|mailto:)[^)]+\)", r"\1", text)
    text = re.sub(r"(?<!\()https?://\S+", "", text)
    return text


def spoken_symbols(text: str) -> str:
    replacements = {
        "⇏": " does not imply ",
        "⇒": " implies ",
        "≠": " does not equal ",
        "≈": " approximately ",
        "±": " plus or minus ",
        "≤": " less than or equal to ",
        "≥": " greater than or equal to ",
        "→": " then ",
        "->": " then ",
        "²": " squared",
        "³": " cubed",
        "λ": "lambda",
        "τ": "tau",
        "ζ": "zeta",
        "Φ": "phi",
        "φ": "phi",
        "ω": "omega",
        "μ": "mu",
        "η": "eta",
        "σ": "sigma",
        "θ": "theta",
        "α": "alpha",
        "Δ": "delta ",
        "Ω": "ohms",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def simplify_inline_math(text: str) -> str:
    # Remove common Markdown/LaTeX wrappers without attempting to re-derive formulas.
    text = text.replace("\\(", "").replace("\\)", "")
    text = text.replace("`", "")
    text = text.replace("\\boxed", "")
    text = text.replace("\\text", "")
    text = text.replace("\\,", " ")
    text = text.replace("\\cdot", " times ")
    text = text.replace("\\times", " times ")
    text = text.replace("\\frac", " fraction ")
    text = text.replace("\\sqrt", " square root of ")
    text = text.replace("\\infty", " infinity ")
    text = text.replace("\\ell", " ell ")
    text = text.replace("\\pi", " pi ")
    text = text.replace("\\", "")
    text = text.replace("{", " ").replace("}", " ")
    text = re.sub(r"\s+", " ", text) if "\n" not in text else text
    return text


def normalize_headings_and_pacing(text: str) -> str:
    """Turn structural Markdown into narration-friendly pacing.

    Title and chapter/section headings remain visibly bold because rich-text importers
    use that structure, but hash marks and low-value production labels are removed.
    """
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue
        if stripped == "---":
            out.extend([""])
            continue
        if stripped.lower() in {
            "### elevenlabs conversational script",
            "### elevenreader conversational script",
        }:
            continue
        if stripped.startswith("#"):
            heading = re.sub(r"^#{1,6}\s*", "", stripped).strip()
            # Canonical research chapters sometimes say Episode; publication says Chapter.
            heading = re.sub(r"^Episode\s+(\d+)\s+", r"Chapter \1 ", heading)
            out.extend(["", f"**{heading}**", ""])
            continue
        if stripped.startswith("- "):
            out.append(stripped[2:].strip())
            continue
        out.append(line)
    return "\n".join(out)


def clean_emphasis(text: str) -> str:
    """Remove emphasis markup except complete-line bold headings."""
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("**") and stripped.endswith("**") and stripped.count("**") == 2:
            out.append(line)
        else:
            out.append(line.replace("**", "").replace("__", "").replace("*", ""))
    return "\n".join(out)


def collapse_blank_lines(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def to_elevenreader(text: str) -> str:
    text = strip_display_math(text)
    text = normalize_tables(text)
    text = remove_markdown_links(text)
    text = normalize_headings_and_pacing(text)
    text = clean_emphasis(text)
    text = spoken_symbols(text)
    text = simplify_inline_math(text)
    text = collapse_blank_lines(text)
    return text


def assemble_elevenreader(manifest: dict) -> str:
    pieces = [
        "**VRX Physics Laboratory**\n\n"
        "**A Spoken Course in Verifiable Electromechanical Systems**\n\n"
        "Shannon Bray\n\n"
        "Lantern Protocol Research Edition\n"
    ]
    for relative in source_sequence(manifest, include_research_appendices=False):
        pieces.append(to_elevenreader(read_source(relative)).rstrip())
    body = "\n\n".join(pieces)
    return collapse_blank_lines(body)


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def build() -> tuple[Path, Path]:
    manifest = load_manifest()
    research_path = BOOK_ROOT / manifest["generated_outputs"]["research"]
    eleven_path = BOOK_ROOT / manifest["generated_outputs"]["elevenreader"]
    write_output(research_path, assemble_research(manifest))
    write_output(eleven_path, assemble_elevenreader(manifest))
    return eleven_path, research_path


def check() -> int:
    manifest = load_manifest()
    expected = {
        BOOK_ROOT / manifest["generated_outputs"]["research"]: assemble_research(manifest),
        BOOK_ROOT / manifest["generated_outputs"]["elevenreader"]: assemble_elevenreader(manifest),
    }
    failures = []
    for path, content in expected.items():
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            failures.append(path)
    if failures:
        print("Generated publication artifacts are stale or missing:")
        for path in failures:
            print(f" - {path.relative_to(BOOK_ROOT)}")
        return 1
    print("Publication artifacts match canonical source.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Verify generated outputs are current")
    args = parser.parse_args()
    if args.check:
        return check()
    eleven, research = build()
    print(f"Wrote {eleven.relative_to(BOOK_ROOT)}")
    print(f"Wrote {research.relative_to(BOOK_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
