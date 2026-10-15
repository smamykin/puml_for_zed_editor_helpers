#!/usr/bin/env python3
"""Render the fenced PlantUML block at a Markdown cursor position locally."""

import argparse

import re
import subprocess
import sys
import tempfile
from pathlib import Path

FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)$")


def extract_block(markdown, row):
    """Return (source, opening line) for a 1-based cursor row, fences included."""
    lines = markdown.splitlines()
    if not 1 <= row <= len(lines):
        raise ValueError("Cursor line is outside the saved document.")
    opening = None
    for index, line in enumerate(lines, 1):
        if opening is None:
            match = FENCE.match(line)
            if match:
                fence, info = match.groups()
                if fence[0] == "`" and "`" in info:
                    continue
                opening = (index, fence, info.strip().lower())
        else:
            start, fence, language = opening
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*", line):
                if start <= row <= index:
                    if language not in ("puml", "plantuml"):
                        raise ValueError("The cursor is in a code block, but its language is not puml or plantuml.")
                    source = "\n".join(lines[start:index - 1]).strip()
                    if not source:
                        raise ValueError("The PlantUML block is empty.")
                    return source, start
                opening = None
    if opening and opening[0] <= row:
        raise ValueError("The code block has no closing fence.")
    raise ValueError("Place the cursor inside a fenced puml or plantuml block.")


def render(source, document, opening_line):
    # Bare diagram bodies are convenient in Markdown; complete @start... forms
    # (including @startmindmap and friends) are passed through unchanged.
    if not re.search(r"(?m)^\s*@start\w+\b", source):
        source = "@startuml\n" + source + "\n@enduml"
    renderer = Path(__file__).resolve().with_name("plantuml")
    result = subprocess.run(
        [str(renderer), "-charset", "UTF-8", "-failfast2", "-tpng", "-pipe"],
        input=source.encode("utf-8"), capture_output=True,
        cwd=document.parent, timeout=60,
    )
    if result.returncode or not result.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError("PlantUML could not render the block at Markdown line "
                         + str(opening_line) + ".\n" + (detail or "No valid PNG was returned."))
    output = document.parent / "_puml_render.png"
    # Replace atomically so viewers never read a partially written PNG.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=document.parent, prefix="._puml_render-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(result.stdout)
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="Saved Markdown document")
    parser.add_argument("row", type=int, help="1-based cursor line (ZED_ROW)")
    parser.add_argument("--no-open", action="store_true", help="Render without opening Preview")
    args = parser.parse_args(argv)
    try:
        document = args.file.expanduser().resolve(strict=True)
        source, opening = extract_block(document.read_text(encoding="utf-8-sig"), args.row)
        output = render(source, document, opening)
        print(output, flush=True)
        if not args.no_open:
            subprocess.run(["/usr/bin/open", "-a", "Preview", str(output)], check=True, timeout=15)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print("PlantUML preview: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
