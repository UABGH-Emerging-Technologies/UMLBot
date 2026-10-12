"""Pure helpers for planning and validating PlantUML Gantt charts.

This module contains no I/O.  It provides three concerns:

* :func:`extract_start_date` -- read an explicit project start date from the
  user's request (never from incidental dates elsewhere in the description).
* :func:`quarter_table` -- build a table of calendar quarters starting from a
  project start date so the model can copy dates instead of doing arithmetic.
* :func:`extract_max_quarters` -- read an explicit project length (R21, R01,
  ``N years``, ``N months``, ``N quarters``) from the user's request.
* :func:`check_gantt_plan` -- validate a rendered Gantt snippet against the
  plan (dates, label consistency, dependency order, span, task count).
* :func:`style_gantt` -- apply deterministic, readable presentation to a Gantt
  snippet (hidden table columns, a sensible axis, one colour per section).
* :func:`plan_total_days` -- measure the plan span in days from its task lines.
* :func:`wants_detailed_plan` -- read whether the request asks for detail.

Public API:
    Quarter
    extract_start_date
    quarter_table
    extract_max_quarters
    check_gantt_plan
    style_gantt
    plan_total_days
    wants_detailed_plan
"""

from __future__ import annotations

import calendar
import math
import re
from dataclasses import dataclass
from datetime import date

# The UI wraps the user's request inside a larger description; this marker
# separates the actual request from the surrounding context.
_USER_REQUEST_MARKER = "Latest user request:"

# Month names (full and common abbreviations) mapped to their month number.
_MONTH_NAMES: dict[str, int] = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

# Month-name alternation used inside the date patterns below.
_MONTH_PATTERN = (
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?"
)

# Ordered date patterns.  ``_parse_first_date`` searches every pattern and keeps
# the match that starts earliest in the text.
_DATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?P<y>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2})"),
    re.compile(r"(?P<y>\d{4})/(?P<m>\d{1,2})/(?P<d>\d{1,2})"),
    re.compile(
        rf"(?P<mon>{_MONTH_PATTERN})\.?\s+(?P<d>\d{{1,2}}),?\s+(?P<y>\d{{4}})", re.IGNORECASE
    ),
    re.compile(
        rf"(?P<d>\d{{1,2}})\s+(?P<mon>{_MONTH_PATTERN})\.?,?\s+(?P<y>\d{{4}})", re.IGNORECASE
    ),
    re.compile(rf"(?P<mon>{_MONTH_PATTERN})\.?\s+(?P<y>\d{{4}})", re.IGNORECASE),
    re.compile(r"(?P<m>\d{1,2})/(?P<y>\d{4})"),
    re.compile(r"(?i)q(?P<q>[1-4])\s+(?P<y>\d{4})"),
]

# Start keywords.  ``start`` is intentionally listed last so the more specific
# phrases win when several keywords overlap at the same position.
_START_KEYWORD_RE = re.compile(
    r"\b(?:project\s+start|start\s+date|kick\s*off|kickoff|award\s+date|funded\s+from|"
    r"commencing|beginning|begins|starting|starts|start)\b",
    re.IGNORECASE,
)

# Number of whitespace-separated words after a start keyword in which a date may
# appear.
_START_WINDOW_WORDS = 6

# ``R21`` (exploratory) is ~2 years; ``R01`` is up to 5 years.
_R_MECHANISM_QUARTERS: dict[str, int] = {"R21": 8, "R01": 20}

# Gantt parsing helpers -----------------------------------------------------
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_D_OFFSET_RE = re.compile(r"D\+(\d+)", re.IGNORECASE)
_STARTS_LINE_RE = re.compile(r"^\s*\[([^\]]+)\]\s+starts\b(.*)$")
_ENDS_LINE_RE = re.compile(r"^\s*\[([^\]]+)\]\s+ends\b(.*)$")
_LASTS_LINE_RE = re.compile(r"^\s*\[([^\]]+)\]\s+lasts\b(.*)$")
_AS_LINE_RE = re.compile(r"^\s*\[([^\]]+)\]\s+as\b(.*)$")
# ``[Label] as [Alias] ...`` -- captures the alias so later lines may use it.
_AS_ALIAS_RE = re.compile(r"^\s*\[[^\]]+\]\s+as\s+\[([^\]]+)\]\s*(.*)$")
# Duration keywords PlantUML accepts after a task or alias declaration.
_DURATION_WORD_RE = re.compile(r"\b(?:lasts|requires)\b", re.IGNORECASE)
_ARROW_RE = re.compile(r"\[([^\]]+)\]\s*-{1,2}>\s*\[([^\]]+)\]")
_STARTS_AT_END_RE = re.compile(
    r"\[([^\]]+)\]\s+starts\s+at\s+\[([^\]]+)\]\s*'s\s+end", re.IGNORECASE
)
_HAPPENS_AT_END_RE = re.compile(
    r"\[([^\]]+)\]\s+happens\s+at\s+\[([^\]]+)\]\s*'s\s+end", re.IGNORECASE
)
_BARE_YEAR_RE = re.compile(r"(?<![\w+-])((?:19|20)\d{2})(?![\w-])")
_PROJECT_STARTS_RE = re.compile(r"^\s*Project\s+starts\b(.*)$", re.IGNORECASE)

# Presentation directives and palette used by :func:`style_gantt`.  The table
# columns are hidden and the footbox removed so only the bars and axis remain.
_HIDE_LINES: tuple[str, ...] = (
    "hide column start",
    "hide column end",
    "hide column duration",
    "show column task",
    "hide footbox",
)

# Task names are listed in the left-hand task column, so the copy PlantUML draws
# on each bar is made invisible.  Milestone labels are not affected.
_BAR_TEXT_STYLE: tuple[str, ...] = (
    "<style>",
    "ganttDiagram {",
    "  task { FontColor transparent }",
    "}",
    "</style>",
)

# A comment line in hand-edited code that opts it in to automatic styling.
AUTO_STYLE_MARKER = "' umlbot: auto-style"

# One colour per section, cycled in order.  Named PlantUML colours are used so
# the directive stays valid without a colour definition block.
_COLOUR_PALETTE: tuple[str, ...] = (
    "LightSteelBlue",
    "Moccasin",
    "Thistle",
    "PaleGreen",
    "LightPink",
    "LightCyan",
)

_PRINTSCALE_LINE_RE = re.compile(r"^\s*printscale\b", re.IGNORECASE)
_ZOOM_LINE_RE = re.compile(r"^\s*zoom\b", re.IGNORECASE)
_SECTION_SEPARATOR_RE = re.compile(r"^\s*--.*--\s*$")
_COLOUR_LINE_RE = re.compile(r"^\s*\[([^\]]+)\]\s+is\s+colored\s+in\b", re.IGNORECASE)

# A plan length is "N-year plan/project/…" or "over/for/spanning N years".  Bare
# phrases such as "1-year mortality" or "12-month follow-up" are not lengths.
_LENGTH_NOUNS = (
    r"(?:plan|project|grant|award|timeline|schedule|study|program|programme|period|"
    r"proposal|r21|r01|gantt|chart)"
)
_LENGTH_PREFIX = r"(?:over|for|spanning|across|lasting|within|covering|of)"


def _length_re(unit: str) -> re.Pattern[str]:
    """Build a pattern matching an ``N <unit>`` phrase that states a plan length."""
    return re.compile(
        rf"(?:\b{_LENGTH_PREFIX}\s+(?:a\s+|the\s+)?(\d+)[-\s]*{unit}\b"
        rf"|\b(\d+)[-\s]*{unit}\s+(?:\w+\s+)?{_LENGTH_NOUNS}\b)",
        re.IGNORECASE,
    )


_YEAR_LENGTH_RE = _length_re(r"(?:years?|yrs?)")
_MONTH_LENGTH_RE = _length_re(r"months?")
_QUARTER_LENGTH_RE = _length_re(r"quarters?")
_R_MECHANISM_RE = re.compile(r"\b(R\d{2})\b", re.IGNORECASE)


@dataclass(frozen=True)
class Quarter:
    """A project quarter with an inclusive calendar end date.

    Attributes:
        label: Project quarter label such as ``"Y1Q1"``.
        start: First calendar day of the quarter.
        end: Inclusive last calendar day of the quarter.
    """

    label: str
    start: date
    end: date


def _user_request_text(description: str) -> str:
    """Return only the user's request portion of ``description``.

    The UI wraps the request in a larger description using a
    ``Latest user request:`` marker.  When that marker is present, only the text
    after it up to the next blank-line-delimited section is searched; otherwise
    the whole description is returned.
    """
    index = description.find(_USER_REQUEST_MARKER)
    if index == -1:
        return description
    remainder = description[index + len(_USER_REQUEST_MARKER) :]
    return remainder.split("\n\n", 1)[0]


def _date_from_match(match: re.Match[str]) -> date | None:
    """Build a :class:`datetime.date` from a date-pattern match, or ``None``."""
    groups = match.groupdict()
    try:
        if groups.get("q"):
            quarter = int(groups["q"])
            return date(int(groups["y"]), (quarter - 1) * 3 + 1, 1)
        if groups.get("mon"):
            month = _MONTH_NAMES.get(groups["mon"].lower())
            if month is None:
                return None
            day = int(groups["d"]) if groups.get("d") else 1
            return date(int(groups["y"]), month, day)
        if groups.get("d") and groups.get("m") and groups.get("y"):
            return date(int(groups["y"]), int(groups["m"]), int(groups["d"]))
        if groups.get("m") and groups.get("y"):
            return date(int(groups["y"]), int(groups["m"]), 1)
    except (TypeError, ValueError):
        return None
    return None


def _parse_first_date(text: str) -> date | None:
    """Return the earliest-parsing date found anywhere in ``text``, or ``None``."""
    best_start: int | None = None
    best_date: date | None = None
    for pattern in _DATE_PATTERNS:
        match = pattern.search(text)
        if match is None:
            continue
        parsed = _date_from_match(match)
        if parsed is None:
            continue
        if best_start is None or match.start() < best_start:
            best_start = match.start()
            best_date = parsed
    return best_date


def extract_start_date(description: str) -> date | None:
    """Return the project start date explicitly stated in the request.

    Only phrases where a start keyword is followed within a few words by a date
    are considered; incidental dates elsewhere are ignored.  Returns ``None`` when
    no such phrase exists or the date is invalid.
    """
    text = _user_request_text(description)
    candidates: list[tuple[int, date]] = []
    for keyword_match in _START_KEYWORD_RE.finditer(text):
        words = text[keyword_match.end() :].split()
        window = " ".join(words[:_START_WINDOW_WORDS])
        parsed = _parse_first_date(window)
        if parsed is not None:
            candidates.append((keyword_match.start(), parsed))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _quarter_end(year: int, quarter: int) -> date:
    """Return the inclusive last day of calendar ``quarter`` in ``year``."""
    end_month = quarter * 3
    last_day = calendar.monthrange(year, end_month)[1]
    return date(year, end_month, last_day)


def quarter_table(start: date, n: int = 20) -> list[Quarter]:
    """Build ``n`` project quarters beginning with the quarter containing ``start``.

    The first row's ``start`` is ``start`` itself (a partial quarter when
    ``start`` is mid-quarter).  Every later row is a full calendar quarter.
    """
    rows: list[Quarter] = []
    year = start.year
    quarter = (start.month - 1) // 3 + 1
    for index in range(n):
        label = f"Y{index // 4 + 1}Q{index % 4 + 1}"
        if index == 0:
            quarter_start = start
        else:
            quarter_start = date(year, (quarter - 1) * 3 + 1, 1)
        rows.append(Quarter(label=label, start=quarter_start, end=_quarter_end(year, quarter)))
        quarter += 1
        if quarter > 4:
            quarter = 1
            year += 1
    return rows


def extract_max_quarters(description: str) -> int | None:
    """Return the project length in quarters stated in the request, or ``None``.

    Explicit lengths take precedence over mechanism names (``R21`` = 8 quarters,
    ``R01`` = 20 quarters).
    """
    text = _user_request_text(description)
    year_match = _YEAR_LENGTH_RE.search(text)
    if year_match:
        return int(year_match.group(1) or year_match.group(2)) * 4
    month_match = _MONTH_LENGTH_RE.search(text)
    if month_match:
        return math.ceil(int(month_match.group(1) or month_match.group(2)) / 3)
    quarter_match = _QUARTER_LENGTH_RE.search(text)
    if quarter_match:
        return int(quarter_match.group(1) or quarter_match.group(2))
    mechanism_match = _R_MECHANISM_RE.search(text)
    if mechanism_match:
        return _R_MECHANISM_QUARTERS.get(mechanism_match.group(1).upper())
    return None


def wants_detailed_plan(description: str) -> bool:
    """Return whether the user's request asks for a detailed plan.

    Only the user-request portion of ``description`` is searched, so the word
    "detailed" appearing elsewhere in a UI-wrapped description does not count.
    """
    return "detailed" in _user_request_text(description).lower()


def plan_total_days(code: str) -> int | None:
    """Return the plan span in days, or ``None`` when nothing is parseable.

    The span is ``latest end - earliest start + 1`` measured from the task
    ``starts``/``ends`` lines: ISO dates in dated charts, ``D+N`` offsets in
    undated charts.  Malformed input never raises.
    """
    try:
        starts_iso: list[date] = []
        ends_iso: list[date] = []
        starts_offset: list[int] = []
        ends_offset: list[int] = []

        for line in code.splitlines():
            starts_match = _STARTS_LINE_RE.match(line)
            if starts_match:
                _collect_span_point(starts_match.group(2), starts_iso, starts_offset)
                continue
            ends_match = _ENDS_LINE_RE.match(line)
            if ends_match:
                _collect_span_point(ends_match.group(2), ends_iso, ends_offset)

        if starts_iso or ends_iso:
            earliest = min(starts_iso) if starts_iso else min(ends_iso)
            latest = max(ends_iso) if ends_iso else max(starts_iso)
            return (latest - earliest).days + 1
        if starts_offset or ends_offset:
            earliest_offset = min(starts_offset) if starts_offset else min(ends_offset)
            latest_offset = max(ends_offset) if ends_offset else max(starts_offset)
            return latest_offset - earliest_offset + 1
        return None
    except Exception:  # pragma: no cover - defensive; measurement must never raise
        return None


def _collect_span_point(rest: str, iso_dates: list[date], offsets: list[int]) -> None:
    """Record an ISO date or ``D+N`` offset parsed from a task line's tail."""
    iso = _ISO_DATE_RE.search(rest)
    if iso is not None:
        parsed = _safe_date(iso.group(0))
        if parsed is not None:
            iso_dates.append(parsed)
        return
    offset = _D_OFFSET_RE.search(rest)
    if offset is not None:
        offsets.append(int(offset.group(1)))


def wants_auto_style(code: str) -> bool:
    """Return whether hand-edited ``code`` opts in to automatic styling."""
    return any(line.strip().lower() == AUTO_STYLE_MARKER for line in code.splitlines())


def style_gantt(
    code: str, *, dated: bool, total_days: int | None, preserve_user_choices: bool = False
) -> str:
    """Apply deterministic, readable presentation to a Gantt snippet.

    The transformation shows task names in a left-hand task column (hiding the
    start/end/duration columns, the footbox and the duplicate text on each bar),
    chooses a sensible axis (monthly/quarterly when dated, a weekly numbered
    axis when undated) and colours every task by its section.  It is pure and
    idempotent: applying it twice returns the same code.  Any failure returns
    ``code`` unchanged.

    With ``preserve_user_choices`` (used for code a person edited by hand and
    marked with :data:`AUTO_STYLE_MARKER`) an existing ``printscale`` line, its
    zoom, any colours and any ``<style>`` block are left exactly as written.
    """
    try:
        lines = code.splitlines()
        if not any(line.strip().startswith("@start") for line in lines):
            return code
        lines = _insert_hide_lines(lines)
        if not _has_style_block(lines):
            lines = _insert_after_hide_lines_block(lines, list(_BAR_TEXT_STYLE))
        if preserve_user_choices:
            if not any(_PRINTSCALE_LINE_RE.match(line) for line in lines):
                lines = _apply_scale(lines, dated=dated, total_days=total_days)
            return "\n".join(lines)
        lines = _apply_scale(lines, dated=dated, total_days=total_days)
        lines = _apply_section_colours(lines)
        return "\n".join(lines)
    except Exception:
        return code


def _has_style_block(lines: list[str]) -> bool:
    """Return whether the code already contains a ``<style>`` block."""
    return any(line.strip().lower() == "<style>" for line in lines)


def _insert_after_hide_lines_block(lines: list[str], block: list[str]) -> list[str]:
    """Insert ``block`` after the last hide/show directive (or the start tag)."""
    last_index: int | None = None
    for index, line in enumerate(lines):
        if line.strip() in _HIDE_LINES:
            last_index = index
    if last_index is None:
        last_index = next(
            (index for index, line in enumerate(lines) if line.strip().startswith("@start")),
            None,
        )
    if last_index is None:
        return lines
    return lines[: last_index + 1] + block + lines[last_index + 1 :]


def _insert_hide_lines(lines: list[str]) -> list[str]:
    """Insert any missing hide directives immediately after the start tag."""
    start_index = next(
        (index for index, line in enumerate(lines) if line.strip().startswith("@start")),
        None,
    )
    if start_index is None:
        return lines
    present = {line.strip() for line in lines}
    missing = [hide for hide in _HIDE_LINES if hide not in present]
    if not missing:
        return lines
    return lines[: start_index + 1] + missing + lines[start_index + 1 :]


def _scale_line(*, dated: bool, total_days: int | None) -> str:
    """Return the axis directive appropriate for the chart's span."""
    if not dated:
        return "printscale weekly with week numbering from 1 zoom 0.5"
    if total_days is not None and total_days <= 400:
        return "printscale monthly"
    return "printscale quarterly"


def _apply_scale(lines: list[str], *, dated: bool, total_days: int | None) -> list[str]:
    """Drop any AI-written zoom clauses and set the single scale line."""
    lines = [line for line in lines if not _ZOOM_LINE_RE.match(line)]
    scale_line = _scale_line(dated=dated, total_days=total_days)
    if any(_PRINTSCALE_LINE_RE.match(line) for line in lines):
        result: list[str] = []
        replaced = False
        for line in lines:
            if _PRINTSCALE_LINE_RE.match(line):
                if not replaced:
                    result.append(scale_line)
                    replaced = True
                continue
            result.append(line)
        return result
    if dated:
        for index, line in enumerate(lines):
            if _PROJECT_STARTS_RE.match(line):
                return lines[: index + 1] + [scale_line] + lines[index + 1 :]
    return _insert_after_hide_lines(lines, scale_line)


def _insert_after_hide_lines(lines: list[str], new_line: str) -> list[str]:
    """Insert ``new_line`` after the last hide directive (or start tag)."""
    last_hide: int | None = None
    for index, line in enumerate(lines):
        if line.strip() in _HIDE_LINES:
            last_hide = index
    if last_hide is not None:
        return lines[: last_hide + 1] + [new_line] + lines[last_hide + 1 :]
    start_index = next(
        (index for index, line in enumerate(lines) if line.strip().startswith("@start")),
        None,
    )
    if start_index is not None:
        return lines[: start_index + 1] + [new_line] + lines[start_index + 1 :]
    return lines + [new_line]


def _apply_section_colours(lines: list[str]) -> list[str]:
    """Colour every task bar by the section it first appears in."""
    existing_colours = {
        match.group(1) for line in lines if (match := _COLOUR_LINE_RE.match(line)) is not None
    }

    task_section: dict[str, int] = {}
    # Tasks before any separator are section 0; the first separator also opens
    # section 0, so a chart that starts with "-- Aim 1 --" begins with colour 0.
    section = 0
    seen_task = False
    seen_separator = False
    for line in lines:
        if _SECTION_SEPARATOR_RE.match(line):
            if seen_task or seen_separator:
                section += 1
            seen_separator = True
            continue
        starts_match = _STARTS_LINE_RE.match(line)
        if starts_match is not None and starts_match.group(1) not in task_section:
            task_section[starts_match.group(1)] = section
            seen_task = True

    labels_with_ends = {
        match.group(1) for line in lines if (match := _ENDS_LINE_RE.match(line)) is not None
    }

    result: list[str] = []
    coloured = set(existing_colours)
    for line in lines:
        result.append(line)
        ends_match = _ENDS_LINE_RE.match(line)
        starts_match = _STARTS_LINE_RE.match(line)
        label: str | None = None
        if ends_match is not None:
            label = ends_match.group(1)
        elif starts_match is not None and starts_match.group(1) not in labels_with_ends:
            label = starts_match.group(1)
        if label is None or label in coloured:
            continue
        section_index = task_section.get(label)
        if section_index is None:
            continue
        colour = _COLOUR_PALETTE[section_index % len(_COLOUR_PALETTE)]
        result.append(f"[{label}] is colored in {colour}")
        coloured.add(label)
    return result


def check_gantt_plan(
    code: str,
    start: date | None,
    quarters: list[Quarter] | None,
    max_quarters: int | None,
    check_dates: bool = True,
    max_tasks: int | None = None,
) -> list[str]:
    """Validate a PlantUML Gantt snippet and return human-readable problems.

    An empty list means the plan is consistent.  Malformed input never raises;
    unparseable lines are skipped.  ``check_dates=False`` skips the date
    allowlist (used when a person edited the code by hand).  When ``max_tasks``
    is given, having more distinct task labels than it is reported.
    """
    problems: list[str] = []
    try:
        _check_gantt_plan_impl(
            code, start, quarters, max_quarters, problems, check_dates, max_tasks
        )
    except Exception:  # pragma: no cover - defensive; parsing must never raise
        return problems
    return problems


def _check_gantt_plan_impl(
    code: str,
    start: date | None,
    quarters: list[Quarter] | None,
    max_quarters: int | None,
    problems: list[str],
    check_dates: bool = True,
    max_tasks: int | None = None,
) -> None:
    """Implementation of :func:`check_gantt_plan` that appends to ``problems``."""
    if quarters is not None and not isinstance(quarters, list):
        quarters = None
    if start is not None and not isinstance(start, date):
        start = None

    lines = [line for line in code.splitlines() if not line.strip().startswith("'")]

    has_start: set[str] = set()
    has_end: set[str] = set()
    declared: set[str] = set()
    starts_dates: dict[str, date] = {}
    starts_offsets: dict[str, int] = {}
    ends_dates: dict[str, date] = {}
    ends_offsets: dict[str, int] = {}
    referenced: set[str] = set()
    dependencies: list[tuple[str, str]] = []
    happens: list[tuple[str, str]] = []

    for line in lines:
        starts_match = _STARTS_LINE_RE.match(line)
        if starts_match:
            label, rest = starts_match.group(1), starts_match.group(2)
            declared.add(label)
            has_start.add(label)
            starts_at_match = _STARTS_AT_END_RE.search(line)
            if starts_at_match:
                prerequisite = starts_at_match.group(2)
                referenced.add(label)
                referenced.add(prerequisite)
                dependencies.append((prerequisite, label))
            else:
                offset = _D_OFFSET_RE.search(rest)
                iso = _ISO_DATE_RE.search(rest)
                if offset:
                    starts_offsets[label] = int(offset.group(1))
                elif iso:
                    parsed = _safe_date(iso.group(0))
                    if parsed is not None:
                        starts_dates[label] = parsed
            continue

        ends_match = _ENDS_LINE_RE.match(line)
        if ends_match:
            label, rest = ends_match.group(1), ends_match.group(2)
            declared.add(label)
            has_end.add(label)
            offset = _D_OFFSET_RE.search(rest)
            iso = _ISO_DATE_RE.search(rest)
            if offset:
                ends_offsets[label] = int(offset.group(1))
            elif iso:
                parsed = _safe_date(iso.group(0))
                if parsed is not None:
                    ends_dates[label] = parsed
            continue

        lasts_match = _LASTS_LINE_RE.match(line)
        if lasts_match:
            declared.add(lasts_match.group(1))
            has_end.add(lasts_match.group(1))
            continue

        alias_match = _AS_ALIAS_RE.match(line)
        if alias_match:
            # The alias is how later lines refer to this task.
            alias = alias_match.group(1)
            declared.add(alias)
            if _DURATION_WORD_RE.search(alias_match.group(2)):
                has_end.add(alias)
                # A task with a duration but no explicit start begins at day 0.
                has_start.add(alias)
            continue

        as_match = _AS_LINE_RE.match(line)
        if as_match:
            declared.add(as_match.group(1))
            if _DURATION_WORD_RE.search(as_match.group(2)):
                has_end.add(as_match.group(1))
            continue

        happens_match = _HAPPENS_AT_END_RE.search(line)
        if happens_match:
            declared.add(happens_match.group(1))
            referenced.add(happens_match.group(2))
            happens.append((happens_match.group(1), happens_match.group(2)))
            continue

        for arrow_match in _ARROW_RE.finditer(line):
            first, second = arrow_match.group(1), arrow_match.group(2)
            referenced.add(first)
            referenced.add(second)
            dependencies.append((first, second))

    if not check_dates:
        pass
    elif start is not None:
        allowed: set[date] = {start}
        if quarters:
            for quarter in quarters:
                allowed.add(quarter.start)
                allowed.add(quarter.end)
        for line in lines:
            for iso in _ISO_DATE_RE.finditer(line):
                parsed = _safe_date(iso.group(0))
                if parsed is not None and parsed not in allowed:
                    problems.append(f"Date {iso.group(0)} is not in the quarter table")
    else:
        for line in lines:
            project_match = _PROJECT_STARTS_RE.match(line)
            dates = _ISO_DATE_RE.findall(line)
            if project_match:
                shown = dates[0] if dates else line.strip()
                problems.append(f"Calendar date {shown} used but the request gave no start date")
            else:
                for shown in dates:
                    problems.append(
                        f"Calendar date {shown} used but the request gave no start date"
                    )
                if not dates:
                    for year in _BARE_YEAR_RE.findall(line):
                        problems.append(f"Year {year} used but the request gave no start date")

    for label in sorted(has_start):
        if label not in has_end:
            problems.append(
                f"Task '{label}' has a start but no end (check the label is spelled identically)"
            )
    for label in sorted(has_end):
        if label not in has_start:
            problems.append(
                f"Task '{label}' has an end but no start (check the label is spelled identically)"
            )

    if max_tasks is not None and len(has_start) > max_tasks:
        problems.append(
            f"Too many tasks ({len(has_start)}); keep the chart high level "
            f"(at most {max_tasks})"
        )

    for label in sorted(referenced):
        if label not in declared:
            problems.append(f"Unknown task '{label}'")

    for prerequisite, dependent in dependencies:
        if start is not None:
            prereq_end = ends_dates.get(prerequisite)
            dep_start = starts_dates.get(dependent)
        else:
            prereq_end = ends_offsets.get(prerequisite)
            dep_start = starts_offsets.get(dependent)
        if prereq_end is not None and dep_start is not None and dep_start <= prereq_end:
            problems.append(f"Task '{dependent}' starts before '{prerequisite}' ends")

    if max_quarters is not None:
        span_end_dates = dict(ends_dates)
        span_end_offsets = dict(ends_offsets)
        for milestone, target in happens:
            if target in ends_dates:
                span_end_dates[milestone] = ends_dates[target]
            if target in ends_offsets:
                span_end_offsets[milestone] = ends_offsets[target]
        _check_span(
            start=start,
            quarters=quarters,
            max_quarters=max_quarters,
            ends_dates=span_end_dates,
            ends_offsets=span_end_offsets,
            problems=problems,
        )


def _check_span(
    start: date | None,
    quarters: list[Quarter] | None,
    max_quarters: int,
    ends_dates: dict[str, date],
    ends_offsets: dict[str, int],
    problems: list[str],
) -> None:
    """Append a problem when the plan extends past ``max_quarters``."""
    if start is not None:
        if not quarters or len(quarters) < max_quarters:
            return
        limit = quarters[max_quarters - 1].end
        latest = max(ends_dates.values(), default=None)
        if latest is not None and latest > limit:
            problems.append(f"Plan runs past the requested {max_quarters} quarters")
        return
    limit_offset = max_quarters * 91 - 1
    latest_offset = max(ends_offsets.values(), default=None)
    if latest_offset is not None and latest_offset > limit_offset:
        problems.append(f"Plan runs past the requested {max_quarters} quarters")


def _safe_date(value: str) -> date | None:
    """Parse an ISO ``YYYY-MM-DD`` string, returning ``None`` when invalid."""
    try:
        year, month, day = (int(part) for part in value.split("-"))
        return date(year, month, day)
    except (TypeError, ValueError):
        return None
