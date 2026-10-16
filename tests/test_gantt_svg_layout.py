"""SVG layout fixes for Gantt charts: fonts, fit loop and title notes."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from UMLBot.config.config import UMLBotConfig
from UMLBot.services.diagram_service import (
    DiagramService,
    _render_gantt,
    _render_plantuml_jar,
)
from UMLBot.utils.gantt_planning import (
    bump_gantt_zoom,
    gantt_layout_ok,
    plan_total_days,
    postprocess_gantt_svg,
    style_gantt,
)

SEVEN_WEEK: str = """@startgantt
title Signal pilot plan (timeline in project weeks; 13 weeks = 1 quarter)
printscale weekly zoom 0.5
Project starts 2026-11-02
-- Signal intake and screening --
[Collect reports] lasts 14 days
[Screen signals] lasts 10 days
[Screen signals] starts at [Collect reports]'s end
-- Event detection and comparison --
[Run detection] lasts 14 days
[Run detection] starts at [Screen signals]'s end
[Compare methods] lasts 7 days
[Compare methods] starts at [Run detection]'s end
@endgantt"""

THIRTEEN_WEEK: str = """@startgantt
Project starts 2027-01-04
title Pilot (13 weeks = 1 quarter)
-- Recruitment and baseline assessment --
[Recruit cohort] starts 2027-01-04
[Recruit cohort] ends 2027-02-15
[Baseline assessment] starts 2027-02-16
[Baseline assessment] ends 2027-03-10
-- Analysis and dissemination planning --
[Analyse outcomes] starts 2027-03-11
[Analyse outcomes] ends 2027-04-04
[Write dissemination plan] starts 2027-02-01
[Write dissemination plan] ends 2027-03-31
@endgantt"""

TWENTY_FOUR_MONTH: str = """@startgantt
Project starts 2027-07-01
title Composite index development (24 months)
-- Aim 1: Develop and validate the composite index --
[Build candidate indicators] starts 2027-07-01
[Build candidate indicators] ends 2028-06-30
[Validate index] starts 2028-07-01
[Validate index] ends 2029-06-30
-- Aim 2: Evaluate the index in external cohorts --
[Assemble cohorts] starts 2027-07-01
[Assemble cohorts] ends 2028-03-31
[Run external validation] starts 2028-04-01
[Run external validation] ends 2028-12-31
-- Aim 3: Dissemination and translation --
[Prepare manuscripts] starts 2028-07-01
[Prepare manuscripts] ends 2029-06-30
[Index locked] happens at [Validate index]'s end
@endgantt"""

THREE_DAY: str = """@startgantt
!theme plain
Project starts 2027-07-01
title BHCI workflow
-- Data preparation --
[A] starts 2027-07-01 and lasts 3 days
@endgantt"""

_SAMPLES: list[tuple[str, str, int]] = [
    ("seven_week", SEVEN_WEEK, 45),
    ("thirteen_week", THIRTEEN_WEEK, 91),
    ("twenty_four_month", TWENTY_FOUR_MONTH, 731),
    ("three_day", THREE_DAY, 3),
]

_TASKS: dict[str, list[str]] = {
    "seven_week": [
        "Collect reports",
        "Screen signals",
        "Run detection",
        "Compare methods",
    ],
    "thirteen_week": [
        "Recruit cohort",
        "Baseline assessment",
        "Analyse outcomes",
        "Write dissemination plan",
    ],
    "twenty_four_month": [
        "Build candidate indicators",
        "Validate index",
        "Assemble cohorts",
        "Run external validation",
        "Prepare manuscripts",
    ],
    "three_day": ["A"],
}

_TITLE_GROUP_RE = re.compile(r'<g class="title"[^>]*>.*?<text[^>]*>(.*?)</text>', re.DOTALL)


def _title_text(svg: str) -> str:
    match = _TITLE_GROUP_RE.search(svg)
    return match.group(1) if match is not None else ""


class TestPlanTotalDaysDurations:
    """Duration, dependency and milestone plans are measured from their real span."""

    @pytest.mark.parametrize("_name,code,expected", _SAMPLES)
    def test_plan_total_days(self, _name: str, code: str, expected: int) -> None:
        assert plan_total_days(code) == expected

    def test_duration_only_task_starts_at_project_start(self) -> None:
        code = "@startgantt\nProject starts 2027-07-01\n[A] lasts 14 days\n@endgantt"
        assert plan_total_days(code) == 14

    def test_undated_duration_starts_at_day_zero(self) -> None:
        code = "@startgantt\n[A] lasts 14 days\n@endgantt"
        assert plan_total_days(code) == 14

    def test_weeks_are_seven_days(self) -> None:
        code = "@startgantt\nProject starts 2027-07-01\n[A] lasts 2 weeks\n@endgantt"
        assert plan_total_days(code) == 14

    def test_starts_at_prerequisite_start(self) -> None:
        code = (
            "@startgantt\nProject starts 2027-07-01\n"
            "[A] lasts 10 days\n[B] lasts 5 days\n[B] starts at [A]'s start\n@endgantt"
        )
        assert plan_total_days(code) == 10

    def test_milestone_date_is_zero_length(self) -> None:
        code = (
            "@startgantt\nProject starts 2027-07-01\n"
            "[A] lasts 10 days\n[M] happens 2027-07-20\n@endgantt"
        )
        assert plan_total_days(code) == 20

    def test_cycle_is_ignored(self) -> None:
        code = (
            "@startgantt\nProject starts 2027-07-01\n"
            "[A] starts at [B]'s end\n[B] starts at [A]'s end\n@endgantt"
        )
        assert plan_total_days(code) is None

    def test_unknown_label_is_ignored(self) -> None:
        code = "@startgantt\n[A] starts at [Ghost]'s end\n@endgantt"
        assert plan_total_days(code) is None


class TestBumpGanttZoom:
    """The zoom bump multiplies the printscale zoom by 1.5."""

    def test_zoom_two_becomes_three(self) -> None:
        assert bump_gantt_zoom("printscale weekly zoom 2") == "printscale weekly zoom 3"

    def test_zoom_three_becomes_four_and_a_half(self) -> None:
        assert bump_gantt_zoom("printscale weekly zoom 3") == "printscale weekly zoom 4.5"

    def test_zoom_four_and_a_half_becomes_six_point_seven_five(self) -> None:
        assert bump_gantt_zoom("printscale weekly zoom 4.5") == "printscale weekly zoom 6.75"

    def test_no_zoom_gains_one_and_a_half(self) -> None:
        assert bump_gantt_zoom("printscale monthly") == "printscale monthly zoom 1.5"

    def test_missing_printscale_is_appended_after_hide_lines(self) -> None:
        code = "@startgantt\nhide footbox\n[A] starts D+0\n@endgantt"
        result = bump_gantt_zoom(code)
        lines = result.splitlines()
        assert lines.index("printscale weekly zoom 3") > lines.index("hide footbox")

    def test_never_raises(self) -> None:
        code = "@startgantt\n[A] starts D+0\n@endgantt"
        assert "printscale weekly zoom 3" in bump_gantt_zoom(code)


class TestPostprocessGanttSvg:
    """The postprocessor strips stretch attributes and rewrites fonts."""

    _SVG = (
        '<svg><g font-family="sans-serif" lengthAdjust="spacing">'
        '<g class="title"><text x="1" y="2" textLength="3">Plan '
        "(timeline in weeks; 13 = 1 quarter)</text></g>"
        '<text x="4" y="5" textLength="6" lengthAdjust="spacing">Hi</text></g></svg>'
    )

    def test_strips_text_length_and_length_adjust(self) -> None:
        result = postprocess_gantt_svg(self._SVG)
        assert "textLength" not in result
        assert "lengthAdjust" not in result

    def test_rewrites_font_family(self) -> None:
        result = postprocess_gantt_svg(self._SVG)
        assert "font-family=\"Arial, 'Liberation Sans', Helvetica, sans-serif\"" in result
        assert 'font-family="sans-serif"' not in result

    def test_strips_title_scale_note(self) -> None:
        result = postprocess_gantt_svg(self._SVG)
        assert "timeline in" not in result
        assert "= 1 quarter" not in result
        assert "Plan" in result

    def test_idempotent(self) -> None:
        once = postprocess_gantt_svg(self._SVG)
        assert postprocess_gantt_svg(once) == once

    def test_not_svg_returned_unchanged(self) -> None:
        assert postprocess_gantt_svg("not svg") == "not svg"


class TestStyleGanttScaleIsCodeOwned:
    """The scale line is always replaced, even for hand-edited code."""

    def test_preserve_user_choices_replaces_printscale(self) -> None:
        code = (
            "@startgantt\nProject starts 2027-07-01\n"
            "printscale weekly zoom 0.5\n"
            "[A] starts 2027-07-01\n[A] ends 2027-09-30\n@endgantt"
        )
        styled = style_gantt(code, dated=True, total_days=92, preserve_user_choices=True)
        assert "printscale weekly zoom 0.5" not in styled
        assert "printscale weekly zoom 2" in styled

    def test_preserve_user_choices_keeps_colours(self) -> None:
        code = (
            "@startgantt\nProject starts 2027-07-01\n"
            "[A] starts 2027-07-01\n[A] ends 2027-09-30\n"
            "[A] is colored in PaleGreen\n@endgantt"
        )
        styled = style_gantt(code, dated=True, total_days=92, preserve_user_choices=True)
        assert "[A] is colored in PaleGreen" in styled


class TestStyleGanttColours:
    """Every distinct non-milestone task is coloured exactly once."""

    @pytest.mark.parametrize("name,code,_expected", _SAMPLES)
    def test_each_task_coloured_once(self, name: str, code: str, _expected: int) -> None:
        styled = style_gantt(code, dated=True, total_days=plan_total_days(code))
        for task in _TASKS[name]:
            assert styled.count(f"[{task}] is colored in") == 1

    def test_milestone_has_no_colour(self) -> None:
        styled = style_gantt(
            TWENTY_FOUR_MONTH, dated=True, total_days=plan_total_days(TWENTY_FOUR_MONTH)
        )
        assert "[Index locked] is colored in" not in styled


class TestStyleGanttTitle:
    """A model-written scale note is stripped from the title."""

    @pytest.mark.parametrize("_name,code,_expected", _SAMPLES)
    def test_title_note_stripped(self, _name: str, code: str, _expected: int) -> None:
        styled = style_gantt(code, dated=True, total_days=plan_total_days(code))
        title_line = next(line for line in styled.splitlines() if line.strip().startswith("title"))
        assert "timeline in" not in title_line
        assert "=" not in title_line

    def test_plain_title_without_note_is_kept(self) -> None:
        code = "@startgantt\nProject starts 2027-07-01\ntitle BHCI workflow\n@endgantt"
        styled = style_gantt(code, dated=True, total_days=1)
        assert "title BHCI workflow" in styled

    def test_non_scale_parenthetical_is_kept(self) -> None:
        code = "@startgantt\nProject starts 2027-07-01\ntitle BHCI R21 (R21)\n@endgantt"
        styled = style_gantt(code, dated=True, total_days=1)
        assert "title BHCI R21 (R21)" in styled


_JAR_AVAILABLE: bool = (
    shutil.which("java") is not None and Path(UMLBotConfig.PLANTUML_JAR_PATH).exists()
)


def _raw_svg(code: str) -> str:
    svg, _status, _ok = _render_plantuml_jar(code, "", "svg")
    assert isinstance(svg, str)
    return svg


@pytest.mark.skipif(not _JAR_AVAILABLE, reason="java or the PlantUML jar is not available")
@pytest.mark.parametrize("name,code,expected", _SAMPLES)
class TestRenderedGanttSvg:
    """Both render paths produce a clean, well-laid-out SVG."""

    def test_render_diagram_from_code(self, name: str, code: str, expected: int) -> None:
        rendered, _status, _url, render_ok, final_code, _problems = (
            DiagramService().render_diagram_from_code(code, mode="gantt", fmt="svg")
        )
        assert render_ok
        assert isinstance(rendered, str)
        assert "textLength" not in rendered
        assert "lengthAdjust" not in rendered
        title = _title_text(rendered)
        assert "timeline in" not in title
        assert "=" not in title
        assert gantt_layout_ok(_raw_svg(final_code))

    def test_generate_path_render_gantt(self, name: str, code: str, expected: int) -> None:
        styled = style_gantt(code, dated=True, total_days=plan_total_days(code))
        rendered, _status, render_ok, final_code = _render_gantt(styled, "status", "svg")
        assert render_ok
        assert isinstance(rendered, str)
        assert "textLength" not in rendered
        assert "lengthAdjust" not in rendered
        title = _title_text(rendered)
        assert "timeline in" not in title
        assert "=" not in title
        assert gantt_layout_ok(_raw_svg(final_code))
