from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

# Colors present in the monochrome-black SVGs that need to become white.
# Maps each source color (case-insensitive hex) to its replacement.
_COLOR_MAP: list[tuple[str, str]] = [
    ("#000", "#fff"),
    ("#374251", "#fff"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert monochrome-black SVGs to monochrome-white (white lines on transparent background).",
    )
    parser.add_argument("input_path", type=Path, help="Input SVG file or directory.")
    parser.add_argument(
        "output_path",
        type=Path,
        nargs="?",
        help="Output SVG file or directory. Defaults to a sibling *_white path.",
    )
    parser.add_argument(
        "--include-static",
        action="store_true",
        help="Also process svg-static directories when the input is a directory.",
    )
    return parser.parse_args()


def default_output_path(input_path: Path) -> Path:
    suffix = input_path.suffix if input_path.is_file() else ""
    stem = input_path.stem if input_path.is_file() else input_path.name
    return input_path.with_name(f"{stem}_white{suffix}")


def iter_svg_files(input_path: Path, include_static: bool) -> Iterable[Path]:
    if input_path.is_file():
        yield input_path
        return

    for path in sorted(input_path.rglob("*.svg")):
        if not include_static and "svg-static" in path.parts:
            continue
        yield path


def _ensure_root_fill_white(svg_text: str) -> str:
    """Add fill="#fff" to the root <svg> element if no fill attribute is already present.

    Without this, elements that carry no explicit fill attribute default to SVG's
    initial fill value (black), which would not be affected by the hex-replacement pass.
    Setting fill="#fff" on the root causes all such elements to inherit white instead.
    Elements with an explicit fill (e.g. fill="none") are unaffected because explicit
    values always override inherited ones.

    Args:
        svg_text: The full text of an SVG document.

    Returns:
        The modified SVG text with fill="#fff" added to the root <svg> element if it had no fill attribute, or the original text if it already had a fill.
    """
    svg_open_re = re.compile(r"(<svg\b[^>]*?)(/>|>)", re.DOTALL | re.IGNORECASE)
    match = svg_open_re.search(svg_text)
    if not match:
        return svg_text
    attrs = match.group(1)
    if re.search(r"\bfill\s*=", attrs, re.IGNORECASE):
        return svg_text  # fill already present (converted by colour-map pass, or was already white)
    insert_pos = match.start(2)
    return svg_text[:insert_pos] + ' fill="#fff"' + svg_text[insert_pos:]


def convert_svg_colors(svg_text: str) -> str:
    """Replace black/dark-grey color values with white throughout an SVG document.

    Args:
        svg_text: The full text of an SVG document.

    Returns:
        The modified SVG text with black/dark-grey colors replaced by white.
    """
    for source, target in _COLOR_MAP:
        # Use a negative lookahead so we don't partially match longer hex codes,
        # e.g. #0001 should not be treated as #000 followed by 1.
        pattern = re.compile(re.escape(source) + r"(?![0-9a-fA-F])", re.IGNORECASE)
        svg_text = pattern.sub(target, svg_text)
    # Ensure elements with no explicit fill inherit white rather than SVG's default black.
    svg_text = _ensure_root_fill_white(svg_text)
    return svg_text


def convert_svg_file(input_file: Path, output_file: Path) -> bool:
    """Convert a single SVG file.  Returns True if any colors were changed.

    Args:
        input_file: The path to the input SVG file.
        output_file: The path to the output SVG file.

    Returns:
        True if any colors were changed, False otherwise.
    """
    svg_text = input_file.read_text(encoding="utf-8")
    converted = convert_svg_colors(svg_text)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(converted, encoding="utf-8")
    return converted != svg_text


def main() -> None:
    args = parse_args()
    input_path = args.input_path.resolve()
    output_path = (args.output_path or default_output_path(input_path)).resolve()

    svg_files = list(iter_svg_files(input_path, include_static=args.include_static))

    if not svg_files:
        print("No SVG files found.")
        return

    converted = 0
    unchanged = 0
    last_folder = None

    for input_file in svg_files:
        target_file = output_path if input_path.is_file() else output_path / input_file.relative_to(input_path)

        if input_file.parent != last_folder:
            print(f"Processing folder: {input_file.parent}")
            last_folder = input_file.parent

        changed = convert_svg_file(input_file=input_file, output_file=target_file)
        if changed:
            converted += 1
        else:
            unchanged += 1

    print(f"Processed {converted + unchanged} SVGs -> {output_path}")
    if unchanged:
        print(f"  {unchanged} SVGs had no color changes (already white or no recognized colors).")


if __name__ == "__main__":
    main()
