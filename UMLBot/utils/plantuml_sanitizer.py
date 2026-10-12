"""Deterministic PlantUML sanitizers applied immediately before rendering.

LLM-generated PlantUML frequently mixes syntax from other diagram tools (Mermaid,
MS Project, ...).  This module provides a single public entry point,
:func:`sanitize_plantuml`, that dispatches to a per-diagram-type hook.  The
sanitizers are intentionally conservative: they only rewrite the specific,
well-understood defects described below and leave everything else untouched.

Supported modes (values match the API request modes):

* ``"gantt"``      -- fix the wrapper, drop bare ``gantt`` lines, convert
  ``N quarters`` / ``N years`` durations to weeks (13 weeks per quarter,
  52 weeks per year), drop unit ``scale`` and
  invalid ``printscale`` directives, turn ``section X`` into ``-- X --``,
  normalise ``milestone`` declarations, and bracket bare task aliases.
* ``"json"``        -- fix the ``@startjson`` / ``@endjson`` wrapper only.
* ``"ui_mockup"``   -- fix the ``@startsalt`` / ``@endsalt`` wrapper only.
* ``"uml"``, ``"mindmap"``, ``"erd"``, ``"c4"`` and any unknown mode -- the
  code is returned unchanged.

Public API:
    sanitize_plantuml
"""

from __future__ import annotations

import re
from typing import Dict

# Wrapper "kind" used for each mode that needs its start/end tags corrected.
_WRAPPER_KIND: Dict[str, str] = {
    "gantt": "gantt",
    "json": "json",
    "ui_mockup": "salt",
}

# A line that contains nothing but the word ``gantt``.
_BARE_GANTT_RE = re.compile(r"^\s*gantt\s*$", re.IGNORECASE)

# A whole-line ``scale <unit>`` directive.  ``printscale`` and numeric scales
# (e.g. ``scale 2``) are intentionally not matched.
_SCALE_UNIT_RE = re.compile(
    r"^\s*scale\s+(?:daily|weekly|monthly|quarterly|yearly)\s*$",
    re.IGNORECASE,
)

# ``printscale <x>`` where <x> is not a real scale (e.g. ``printscale true``).
_BAD_PRINTSCALE_RE = re.compile(
    r"^\s*printscale\s+(?!(?:daily|weekly|monthly|quarterly|yearly)\b)\S.*$",
    re.IGNORECASE,
)

# Mermaid-style ``section Name`` -> ``-- Name --``.
_SECTION_RE = re.compile(r"^(\s*)section\s+(.+?)\s*$", re.IGNORECASE)

# ``lasts N quarters`` / ``lasts N quarter`` -> ``lasts (N * 13) weeks``.
_QUARTER_DURATION_RE = re.compile(r"\blasts\s+(\d+)\s+quarters?\b", re.IGNORECASE)

# ``lasts N years`` / ``lasts N year`` -> ``lasts (N * 52) weeks``.
_YEAR_DURATION_RE = re.compile(r"\blasts\s+(\d+)\s+years?\b", re.IGNORECASE)

# ``milestone "Label" as M1`` -> ``[Label] as [M1]``.
_MILESTONE_RE = re.compile(r'milestone\s+"([^"]*)"\s+as\s+(\S+)', re.IGNORECASE)

# ``[Label] as T1 ...`` -- an alias declared without brackets.
_BARE_ALIAS_DECL_RE = re.compile(r"^(\s*\[[^\]]+\]\s+as\s+)([A-Za-z_]\w*)(?=\s|$)")

_START_TAG_RE = re.compile(r"@start\w+")
_END_TAG_RE = re.compile(r"@end\w+")


def sanitize_plantuml(code: str, mode: str) -> str:
    """Return ``code`` with deterministic, per-diagram-type repairs applied.

    Args:
        code: The PlantUML source to sanitize.
        mode: Diagram mode, one of ``"uml"``, ``"mindmap"``, ``"ui_mockup"``,
            ``"gantt"``, ``"erd"``, ``"json"`` or ``"c4"``.  Unknown modes
            return ``code`` unchanged.

    Returns:
        The sanitized PlantUML source.  For modes without a sanitizer the input
        is returned verbatim.
    """
    if mode == "gantt":
        return _sanitize_gantt(code)
    if mode in ("json", "ui_mockup"):
        return _fix_wrapper(code, _WRAPPER_KIND[mode])
    return code


def _sanitize_gantt(code: str) -> str:
    """Apply every Gantt-specific repair to ``code``."""
    lines = _fix_wrapper(code, "gantt").splitlines()
    result: list[str] = []
    for line in lines:
        if _BARE_GANTT_RE.match(line):
            continue
        if _SCALE_UNIT_RE.match(line) or _BAD_PRINTSCALE_RE.match(line):
            continue
        line = _SECTION_RE.sub(r"\1-- \2 --", line)
        line = _QUARTER_DURATION_RE.sub(_weeks_from_quarters, line)
        line = _YEAR_DURATION_RE.sub(_weeks_from_years, line)
        line = _MILESTONE_RE.sub(_bracket_milestone, line)
        result.append(line)
    return "\n".join(_bracket_bare_aliases(result))


def _bracket_bare_aliases(lines: list[str]) -> list[str]:
    """Bracket task aliases declared or referenced without ``[...]``.

    ``[Label] as T1 lasts ...`` becomes ``[Label] as [T1] lasts ...``, and later
    uses such as ``T1 starts ...`` or ``T1 --> T2`` become ``[T1] starts ...`` and
    ``[T1] --> [T2]``.  Only aliases declared via ``as`` are touched, only on lines
    that begin with ``[`` or with such an alias, and never inside an existing
    ``[...]`` label, so ``Project starts``, titles and comments stay unchanged.
    """
    aliases: set[str] = set()
    declared: list[str] = []
    for line in lines:
        match = _BARE_ALIAS_DECL_RE.match(line)
        if match:
            aliases.add(match.group(2))
            line = f"{match.group(1)}[{match.group(2)}]{line[match.end(2):]}"
        declared.append(line)
    if not aliases:
        return declared

    alias_re = re.compile(
        r"(?<![\w\[])(" + "|".join(re.escape(a) for a in sorted(aliases)) + r")(?![\w\]])"
    )
    result: list[str] = []
    for line in declared:
        stripped = line.lstrip()
        first_token = re.match(r"[\w]+", stripped)
        if stripped.startswith("[") or (first_token and first_token.group(0) in aliases):
            # Only rewrite text outside existing [...] groups.
            parts = re.split(r"(\[[^\]]*\])", line)
            line = "".join(
                part if part.startswith("[") else alias_re.sub(r"[\1]", part) for part in parts
            )
        result.append(line)
    return result


def _fix_wrapper(code: str, kind: str) -> str:
    """Force the PlantUML start/end wrapper to ``@start<kind>`` / ``@end<kind>``.

    The first ``@start...`` line and the last ``@end...`` line are rewritten to
    the requested ``kind``.  When the code has no ``@start...`` line at all, the
    correct wrapper pair is added around the whole snippet.
    """
    lines = code.splitlines()
    start_index: int | None = None
    end_index: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if start_index is None and stripped.startswith("@start"):
            start_index = index
        if stripped.startswith("@end"):
            end_index = index

    if start_index is None:
        body = "\n".join(line for line in lines if not line.strip().startswith("@end"))
        return f"@start{kind}\n{body}\n@end{kind}"

    lines[start_index] = _START_TAG_RE.sub(f"@start{kind}", lines[start_index])
    if end_index is not None:
        lines[end_index] = _END_TAG_RE.sub(f"@end{kind}", lines[end_index])
    return "\n".join(lines)


def _weeks_from_quarters(match: re.Match[str]) -> str:
    """Rewrite ``lasts N quarters`` as ``lasts (N * 13) weeks``."""
    return f"lasts {int(match.group(1)) * 13} weeks"


def _weeks_from_years(match: re.Match[str]) -> str:
    """Rewrite ``lasts N years`` as ``lasts (N * 52) weeks``."""
    return f"lasts {int(match.group(1)) * 52} weeks"


def _bracket_milestone(match: re.Match[str]) -> str:
    """Rewrite ``milestone "Label" as M1`` as ``[Label] as [M1]``."""
    label = match.group(1)
    milestone_id = match.group(2).strip("[]")
    return f"[{label}] as [{milestone_id}]"
