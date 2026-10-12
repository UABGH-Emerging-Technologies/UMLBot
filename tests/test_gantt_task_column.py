"""Task-column layout: names listed once on the left, separators kept, opt-in for hand edits."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from UMLBot.config.config import UMLBotConfig
from UMLBot.utils.gantt_planning import (
    AUTO_STYLE_MARKER,
    plan_total_days,
    style_gantt,
    wants_auto_style,
)

_TASKS: list[str] = [
    "Develop BHCI algorithm",
    "Construct validity testing",
    "Early warning analysis",
    "Aim 1 manuscript",
]
_MILESTONES: list[str] = ["BHCI locked"]
_SECTIONS: list[str] = [
    "Aim 1: Develop & Validate BHCI",
    "Aim 2: Early Warning Evaluation",
    "Dissemination",
]

# Quarterly R21 chart as the AI writes it (dated: the request gave a start date).
_DATED_AI_CODE: str = """@startgantt
Project starts 2027-07-01
title BHCI R21
-- Aim 1: Develop & Validate BHCI --
[Develop BHCI algorithm] starts 2027-07-01
[Develop BHCI algorithm] ends 2027-12-31
[Construct validity testing] starts 2028-01-01
[Construct validity testing] ends 2028-06-30
[BHCI locked] happens at [Construct validity testing]'s end
-- Aim 2: Early Warning Evaluation --
[Early warning analysis] starts 2027-10-01
[Early warning analysis] ends 2028-12-31
-- Dissemination --
[Aim 1 manuscript] starts 2029-01-01
[Aim 1 manuscript] ends 2029-03-31
@endgantt"""

# Same plan without a start date (week axis).
_UNDATED_AI_CODE: str = """@startgantt
title BHCI R21
-- Aim 1: Develop & Validate BHCI --
[Develop BHCI algorithm] starts D+0
[Develop BHCI algorithm] ends D+181
[Construct validity testing] starts D+182
[Construct validity testing] ends D+363
[BHCI locked] happens at [Construct validity testing]'s end
-- Aim 2: Early Warning Evaluation --
[Early warning analysis] starts D+91
[Early warning analysis] ends D+545
-- Dissemination --
[Aim 1 manuscript] starts D+546
[Aim 1 manuscript] ends D+636
@endgantt"""


def _styled(code: str, dated: bool) -> str:
    return style_gantt(code, dated=dated, total_days=plan_total_days(code))


class TestTaskColumnDirectives:
    """The styled code lists task names in a left column and blanks the bar text."""

    @pytest.mark.parametrize("code,dated", [(_DATED_AI_CODE, True), (_UNDATED_AI_CODE, False)])
    def test_task_column_shown_and_number_columns_hidden(self, code: str, dated: bool) -> None:
        styled = _styled(code, dated)
        for line in (
            "show column task",
            "hide column start",
            "hide column end",
            "hide column duration",
        ):
            assert styled.count(line) == 1

    @pytest.mark.parametrize("code,dated", [(_DATED_AI_CODE, True), (_UNDATED_AI_CODE, False)])
    def test_bar_text_style_added_once_and_idempotent(self, code: str, dated: bool) -> None:
        styled = _styled(code, dated)
        assert styled.count("task { FontColor transparent }") == 1
        assert _styled(styled, dated) == styled

    def test_dated_chart_uses_quarterly_axis(self) -> None:
        assert "printscale quarterly" in _styled(_DATED_AI_CODE, True)

    def test_existing_style_block_is_not_overwritten(self) -> None:
        code = _DATED_AI_CODE.replace(
            "title BHCI R21",
            "<style>\nganttDiagram {\n  task { FontColor red }\n}\n</style>\ntitle BHCI R21",
        )
        styled = _styled(code, True)
        assert "FontColor red" in styled
        assert "FontColor transparent" not in styled


class TestOptInForHandEdits:
    """Hand-edited code is only styled when it carries the opt-in marker."""

    def test_marker_detected(self) -> None:
        assert wants_auto_style(f"@startgantt\n{AUTO_STYLE_MARKER}\n[A] starts D+0\n@endgantt")

    def test_no_marker_means_no_styling(self) -> None:
        assert not wants_auto_style(_DATED_AI_CODE)

    def test_marker_in_a_task_label_does_not_count(self) -> None:
        assert not wants_auto_style("@startgantt\n[umlbot: auto-style] starts D+0\n@endgantt")


_JAR_AVAILABLE: bool = (
    shutil.which("java") is not None and Path(UMLBotConfig.PLANTUML_JAR_PATH).exists()
)


def _render_svg_texts(code: str) -> list[str]:
    """Render ``code`` to SVG with the real PlantUML jar and return every text element."""
    proc = subprocess.run(
        ["java", "-jar", UMLBotConfig.PLANTUML_JAR_PATH, "-tsvg", "-pipe"],
        input=code.encode("utf-8"),
        capture_output=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")
    svg = proc.stdout.decode("utf-8")
    texts = re.findall(r"<text[^>]*>([^<]*)</text>", svg)
    return [t.replace("&amp;", "&") for t in texts]


@pytest.mark.skipif(not _JAR_AVAILABLE, reason="java or the PlantUML jar is not available")
@pytest.mark.parametrize("code,dated", [(_DATED_AI_CODE, True), (_UNDATED_AI_CODE, False)])
def test_each_task_name_rendered_exactly_once(code: str, dated: bool) -> None:
    texts = _render_svg_texts(_styled(code, dated))
    for task in _TASKS:
        assert texts.count(task) == 1, f"{task!r} rendered {texts.count(task)} times"
    # Milestones are listed in the task column and also labelled beside the diamond.
    for milestone in _MILESTONES:
        assert texts.count(milestone) == 2


@pytest.mark.skipif(not _JAR_AVAILABLE, reason="java or the PlantUML jar is not available")
@pytest.mark.parametrize("code,dated", [(_DATED_AI_CODE, True), (_UNDATED_AI_CODE, False)])
def test_section_separators_still_rendered(code: str, dated: bool) -> None:
    texts = _render_svg_texts(_styled(code, dated))
    for section in _SECTIONS:
        assert section in texts, f"separator {section!r} missing"


@pytest.mark.skipif(not _JAR_AVAILABLE, reason="java or the PlantUML jar is not available")
def test_unstyled_chart_duplicates_names() -> None:
    # Guards the test above: without the bar-text style the names really do appear twice.
    styled = _styled(_DATED_AI_CODE, True)
    unstyled = styled.replace("  task { FontColor transparent }\n", "")
    texts = _render_svg_texts(unstyled)
    assert texts.count("Develop BHCI algorithm") == 2
