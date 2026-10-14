"""Unit tests for the deterministic PlantUML sanitizer."""

import re
import shutil
from pathlib import Path

import pytest

from UMLBot.config.config import UMLBotConfig
from UMLBot.utils.gantt_planning import plan_total_days, style_gantt
from UMLBot.utils.plantuml_sanitizer import sanitize_plantuml

GANTT_FIXTURE = """@startuml
!theme plain

Project starts 2027-01-01
printscale quarterly
scale quarterly
title High-Level Gantt: SAH Brain-Heart Coupling Index (BHCI) R21

[Project setup & data harmonization] as [Setup] lasts 1 quarter
[Signal preprocessing & quality control] as [Preprocess] lasts 2 quarters
[Lock BHCI formulation] as [Lock] lasts 1 quarter
[Setup] starts 2027-01-01
[Preprocess] starts at [Setup]'s end
[Lock] starts at [Preprocess]'s end
milestone "BHCI locked" as M1 happens at [Lock]'s end
@enduml"""

GANTT_FIXTURE_EXPECTED = """@startgantt
!theme plain

Project starts 2027-01-01
printscale quarterly
title High-Level Gantt: SAH Brain-Heart Coupling Index (BHCI) R21

[Project setup & data harmonization] as [Setup] lasts 13 weeks
[Signal preprocessing & quality control] as [Preprocess] lasts 26 weeks
[Lock BHCI formulation] as [Lock] lasts 13 weeks
[Setup] starts 2027-01-01
[Preprocess] starts at [Setup]'s end
[Lock] starts at [Preprocess]'s end
[BHCI locked] as [M1] happens at [Lock]'s end
@endgantt"""


class TestGanttFixture:
    """The real production failure is fully repaired."""

    def test_full_fixture_is_repaired(self) -> None:
        assert sanitize_plantuml(GANTT_FIXTURE, "gantt") == GANTT_FIXTURE_EXPECTED


# Real production output: aliases declared and used without brackets.
GANTT_BARE_ALIAS_FIXTURE = """@startgantt
' High-level Gantt diagram (quarters)

Project starts 2024-01-01

[Q1 2024: Project Kickoff & IRB] as Q1_2024 lasts 3 months
[Q2 2024: Data Preprocessing] as Q2_2024 lasts 3 months
Q2_2024 starts 2024-04-01

[Q3 2024: Feature Extraction & Algorithm Development] as Q3_2024 lasts 3 months
Q3_2024 starts 2024-07-01

[Q4 2024: Internal Validation] as Q4_2024 lasts 3 months
Q4_2024 starts 2024-10-01

[Q1 2025: Threshold Definition] as Q1_2025 lasts 3 months
Q1_2025 starts 2025-01-01

[Q2 2025: Early Warning Evaluation] as Q2_2025 lasts 3 months
Q2_2025 starts 2025-04-01

[Q3 2025: Manuscript Preparation] as Q3_2025 lasts 3 months
Q3_2025 starts 2025-07-01

[Q4 2025: Dissemination & R01 Planning] as Q4_2025 lasts 3 months
Q4_2025 starts 2025-10-01

' Dependencies
Q1_2024 --> Q2_2024
Q2_2024 --> Q3_2024
Q3_2024 --> Q4_2024
Q4_2024 --> Q1_2025
Q1_2025 --> Q2_2025
Q2_2025 --> Q3_2025
Q3_2025 --> Q4_2025
@endgantt"""

GANTT_BARE_ALIAS_EXPECTED = """@startgantt
' High-level Gantt diagram (quarters)

Project starts 2024-01-01

[Q1 2024: Project Kickoff & IRB] as [Q1_2024] lasts 3 months
[Q2 2024: Data Preprocessing] as [Q2_2024] lasts 3 months
[Q2_2024] starts 2024-04-01

[Q3 2024: Feature Extraction & Algorithm Development] as [Q3_2024] lasts 3 months
[Q3_2024] starts 2024-07-01

[Q4 2024: Internal Validation] as [Q4_2024] lasts 3 months
[Q4_2024] starts 2024-10-01

[Q1 2025: Threshold Definition] as [Q1_2025] lasts 3 months
[Q1_2025] starts 2025-01-01

[Q2 2025: Early Warning Evaluation] as [Q2_2025] lasts 3 months
[Q2_2025] starts 2025-04-01

[Q3 2025: Manuscript Preparation] as [Q3_2025] lasts 3 months
[Q3_2025] starts 2025-07-01

[Q4 2025: Dissemination & R01 Planning] as [Q4_2025] lasts 3 months
[Q4_2025] starts 2025-10-01

' Dependencies
[Q1_2024] --> [Q2_2024]
[Q2_2024] --> [Q3_2024]
[Q3_2024] --> [Q4_2024]
[Q4_2024] --> [Q1_2025]
[Q1_2025] --> [Q2_2025]
[Q2_2025] --> [Q3_2025]
[Q3_2025] --> [Q4_2025]
@endgantt"""


class TestGanttBareAliases:
    """Aliases written without ``[...]`` are bracketed everywhere they are used."""

    def test_real_fixture_is_repaired(self) -> None:
        assert sanitize_plantuml(GANTT_BARE_ALIAS_FIXTURE, "gantt") == GANTT_BARE_ALIAS_EXPECTED

    def test_already_bracketed_alias_unchanged(self) -> None:
        code = "@startgantt\n[Design] as [D] lasts 2 days\n[E] starts at [D]'s end\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == code

    def test_alias_word_in_label_title_and_comment_untouched(self) -> None:
        code = (
            "@startgantt\ntitle Plan for D\n' D is design\n[Do D work] as D lasts 2 days\n"
            "[Review] starts at D's end\nD -> [Review]\n@endgantt"
        )
        expected = (
            "@startgantt\ntitle Plan for D\n' D is design\n[Do D work] as [D] lasts 2 days\n"
            "[Review] starts at [D]'s end\n[D] -> [Review]\n@endgantt"
        )
        assert sanitize_plantuml(code, "gantt") == expected

    def test_alias_prefix_does_not_match_longer_alias(self) -> None:
        code = "@startgantt\n[A] as T1 lasts 1 day\n[B] as T10 lasts 1 day\nT10 starts at T1's end\n@endgantt"
        expected = (
            "@startgantt\n[A] as [T1] lasts 1 day\n[B] as [T10] lasts 1 day\n"
            "[T10] starts at [T1]'s end\n@endgantt"
        )
        assert sanitize_plantuml(code, "gantt") == expected

    def test_project_starts_line_untouched(self) -> None:
        code = "@startgantt\nProject starts 2024-01-01\n[A] as A1 lasts 1 day\n@endgantt"
        assert "\nProject starts 2024-01-01\n" in sanitize_plantuml(code, "gantt")

    def test_sanitizer_is_idempotent(self) -> None:
        once = sanitize_plantuml(GANTT_BARE_ALIAS_FIXTURE, "gantt")
        assert sanitize_plantuml(once, "gantt") == once

    def test_uml_component_alias_untouched(self) -> None:
        code = "@startuml\n[Comp] as C1\nC1 --> C2\n@enduml"
        assert sanitize_plantuml(code, "uml") == code


# Real production output: Mermaid-style sections, ``printscale true`` and quarters.
GANTT_SECTION_FIXTURE = """@startgantt
' R21 Project Timeline - Brain-Heart Coupling Index (BHCI)
' High-level Gantt chart by calendar quarters

Project starts 2024-01-01
scale quarterly
printscale true
title Brain-Heart Coupling Index (BHCI) – R21 Gantt Overview

section Year 1 (2024)
  [Kickoff & Infrastructure Setup]         lasts 1 quarter
  [Data Extraction & Quality Assurance]    starts 2024-01-01 lasts 2 quarters
  [BHCI Algorithm Development (Aim 1)]     starts 2024-04-01 lasts 2 quarters
  [Internal Validation & Lock BHCI]        starts 2024-10-01 lasts 2 quarters

section Year 2 (2025)
  [Early Warning Analysis (Aim 2)]         starts 2025-01-01 lasts 2 quarters
  [Impact Assessment & Dissemination]      starts 2025-07-01 lasts 1 quarter
  [R01 Grant Preparation]                  starts 2025-10-01 lasts 1 quarter
@endgantt"""


class TestGanttSectionsAndScales:
    """Mermaid ``section`` lines, bogus ``printscale`` values and year durations."""

    def test_section_becomes_separator(self) -> None:
        code = "@startgantt\nsection Year 1 (2024)\n[A] lasts 1 day\n@endgantt"
        assert "\n-- Year 1 (2024) --\n" in sanitize_plantuml(code, "gantt")

    def test_invalid_printscale_removed(self) -> None:
        code = "@startgantt\nprintscale true\n[A] lasts 1 day\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == "@startgantt\n[A] lasts 1 day\n@endgantt"

    def test_valid_printscale_with_zoom_kept(self) -> None:
        code = "@startgantt\nprintscale daily zoom 2\n[A] lasts 1 day\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == code

    def test_year_duration_becomes_weeks(self) -> None:
        code = "@startgantt\n[A] lasts 1 year\n[B] lasts 2 years\n@endgantt"
        expected = "@startgantt\n[A] lasts 52 weeks\n[B] lasts 104 weeks\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == expected

    def test_section_word_in_label_untouched(self) -> None:
        code = "@startgantt\n[Write section 2] lasts 1 day\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == code

    def test_real_fixture_has_no_known_defects(self) -> None:
        out = sanitize_plantuml(GANTT_SECTION_FIXTURE, "gantt")
        assert "section " not in out
        assert "printscale true" not in out
        assert "scale quarterly" not in out
        assert not re.search(r"lasts \d+ quarters?", out)
        assert sanitize_plantuml(out, "gantt") == out


class TestGanttDefects:
    """Each defect in the table maps to its expected output."""

    def test_wrapper_replaced(self) -> None:
        code = "@startuml\n[Task] lasts 1 day\n@enduml"
        assert sanitize_plantuml(code, "gantt") == "@startgantt\n[Task] lasts 1 day\n@endgantt"

    def test_bare_gantt_line_removed(self) -> None:
        code = "@startgantt\ngantt\n[Task] lasts 1 day\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == "@startgantt\n[Task] lasts 1 day\n@endgantt"

    def test_bare_gantt_line_case_insensitive(self) -> None:
        code = "@startgantt\nGANTT\n[Task] lasts 1 day\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == "@startgantt\n[Task] lasts 1 day\n@endgantt"

    def test_quarter_duration_becomes_weeks(self) -> None:
        code = "@startgantt\n[Task] lasts 1 quarter\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == "@startgantt\n[Task] lasts 13 weeks\n@endgantt"

    def test_plural_quarter_duration_becomes_weeks(self) -> None:
        code = "@startgantt\n[Task] lasts 2 quarters\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == "@startgantt\n[Task] lasts 26 weeks\n@endgantt"

    def test_scale_unit_line_removed(self) -> None:
        code = "@startgantt\nscale quarterly\n[Task] lasts 1 day\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == "@startgantt\n[Task] lasts 1 day\n@endgantt"

    def test_milestone_syntax_normalised(self) -> None:
        code = '@startgantt\nmilestone "BHCI locked" as M1 happens at [Lock]\'s end\n@endgantt'
        assert sanitize_plantuml(code, "gantt") == (
            "@startgantt\n[BHCI locked] as [M1] happens at [Lock]'s end\n@endgantt"
        )


class TestGanttNoOps:
    """Valid Gantt constructs and unrelated content must be preserved."""

    def test_title_with_gantt_word_untouched(self) -> None:
        code = "@startgantt\ntitle My Gantt Chart\n[Task] lasts 1 day\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == code

    def test_task_label_with_gantt_word_untouched(self) -> None:
        code = "@startgantt\n[Gantt review] lasts 1 day\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == code

    def test_printscale_preserved(self) -> None:
        code = "@startgantt\nprintscale quarterly\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == code

    def test_numeric_scale_preserved(self) -> None:
        code = "@startgantt\nscale 2\n[Task] lasts 1 day\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == code

    def test_months_duration_preserved(self) -> None:
        code = "@startgantt\n[Task] lasts 3 months\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == code

    def test_section_separator_preserved(self) -> None:
        code = "@startgantt\n-- Section --\n[Task] lasts 1 day\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == code

    def test_start_without_wrapper_adds_pair(self) -> None:
        code = "[Task] lasts 1 day"
        assert sanitize_plantuml(code, "gantt") == "@startgantt\n[Task] lasts 1 day\n@endgantt"

    def test_missing_start_with_stray_end_not_doubled(self) -> None:
        code = "[Task] lasts 1 day\n@enduml"
        assert sanitize_plantuml(code, "gantt") == "@startgantt\n[Task] lasts 1 day\n@endgantt"


class TestOtherModes:
    """json and ui_mockup fix only the wrapper; other modes are no-ops."""

    def test_json_wrapper_fixed(self) -> None:
        code = '@startuml\n{\n  "a": 1\n}\n@enduml'
        assert sanitize_plantuml(code, "json") == '@startjson\n{\n  "a": 1\n}\n@endjson'

    def test_json_correct_wrapper_unchanged(self) -> None:
        code = '@startjson\n{\n  "a": 1\n}\n@endjson'
        assert sanitize_plantuml(code, "json") == code

    def test_ui_mockup_wrapper_fixed(self) -> None:
        code = "@startuml\n{button}\n@enduml"
        assert sanitize_plantuml(code, "ui_mockup") == "@startsalt\n{button}\n@endsalt"

    def test_uml_class_field_quarter_unchanged(self) -> None:
        code = "@startuml\nclass Report {\n  quarter : int\n}\n@enduml"
        assert sanitize_plantuml(code, "uml") == code

    def test_mindmap_unchanged(self) -> None:
        code = "@startmindmap\n* Root\n** Child\n@endmindmap"
        assert sanitize_plantuml(code, "mindmap") == code

    def test_erd_unchanged(self) -> None:
        code = '@startuml\nentity "E" {\n  *id : int\n}\n@enduml'
        assert sanitize_plantuml(code, "erd") == code

    def test_c4_unchanged(self) -> None:
        code = "@startuml\n!include C4_Context.puml\n@enduml"
        assert sanitize_plantuml(code, "c4") == code

    def test_unknown_mode_unchanged(self) -> None:
        code = "@startuml\nscale quarterly\ngantt\n@enduml"
        assert sanitize_plantuml(code, "mystery") == code


GANTT_UNDATED_FIXTURE = """@startgantt
printscale weekly with week numbering from 1 zoom 0.5
title T (timeline in project weeks; 13 weeks = 1 quarter)
-- Aim 1 --
[A task] starts D+0
[A task] ends D+181
[B task] starts D+182
[B task] ends D+272
-- Aim 2 --
[C task] starts D+91
[C task] ends D+272
[A task] -> [B task]
[M done] happens at [B task]'s end
@endgantt"""

GANTT_DATED_FIXTURE = """@startgantt
Project starts 2027-07-01
printscale quarterly
[A] starts 2027-07-01
[A] ends 2027-12-31
[B] starts 2028-01-01
[B] ends 2028-06-30
[C] starts 2027-10-01
[C] ends 2028-03-31
[A] -> [B]
[C] -> [B]
@endgantt"""


@pytest.mark.skipif(
    shutil.which("java") is None or not Path(UMLBotConfig.PLANTUML_JAR_PATH).exists(),
    reason="java or the PlantUML jar is not available",
)
@pytest.mark.parametrize(
    "fixture",
    [
        GANTT_FIXTURE,
        GANTT_BARE_ALIAS_FIXTURE,
        GANTT_SECTION_FIXTURE,
        GANTT_UNDATED_FIXTURE,
        GANTT_DATED_FIXTURE,
    ],
)
def test_sanitized_fixture_renders_with_real_jar(fixture: str) -> None:
    from UMLBot.services.diagram_service import _render_plantuml_jar

    image, _, render_ok = _render_plantuml_jar(
        plantuml_code=sanitize_plantuml(fixture, "gantt"),
        status_msg="test render",
    )

    assert render_ok is True
    assert image is not None


@pytest.mark.skipif(
    shutil.which("java") is None or not Path(UMLBotConfig.PLANTUML_JAR_PATH).exists(),
    reason="java or the PlantUML jar is not available",
)
@pytest.mark.parametrize(
    ("fixture", "dated"),
    [
        (GANTT_UNDATED_FIXTURE, False),
        (GANTT_DATED_FIXTURE, True),
    ],
)
def test_styled_fixture_renders_with_real_jar(fixture: str, dated: bool) -> None:
    from UMLBot.services.diagram_service import _render_plantuml_jar

    styled = style_gantt(fixture, dated=dated, total_days=plan_total_days(fixture))
    image, _, render_ok = _render_plantuml_jar(
        plantuml_code=styled,
        status_msg="test render",
    )

    assert render_ok is True
    assert image is not None
