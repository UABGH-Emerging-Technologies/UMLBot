"""Unit tests for the deterministic PlantUML sanitizer."""

import shutil
from pathlib import Path

import pytest

from UMLBot.config.config import UMLBotConfig
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

[Project setup & data harmonization] as [Setup] lasts 3 months
[Signal preprocessing & quality control] as [Preprocess] lasts 6 months
[Lock BHCI formulation] as [Lock] lasts 3 months
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

    def test_quarter_duration_becomes_months(self) -> None:
        code = "@startgantt\n[Task] lasts 1 quarter\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == "@startgantt\n[Task] lasts 3 months\n@endgantt"

    def test_plural_quarter_duration_becomes_months(self) -> None:
        code = "@startgantt\n[Task] lasts 2 quarters\n@endgantt"
        assert sanitize_plantuml(code, "gantt") == "@startgantt\n[Task] lasts 6 months\n@endgantt"

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


@pytest.mark.skipif(
    shutil.which("java") is None or not Path(UMLBotConfig.PLANTUML_JAR_PATH).exists(),
    reason="java or the PlantUML jar is not available",
)
@pytest.mark.parametrize("fixture", [GANTT_FIXTURE, GANTT_BARE_ALIAS_FIXTURE])
def test_sanitized_fixture_renders_with_real_jar(fixture: str) -> None:
    from UMLBot.services.diagram_service import _render_plantuml_jar

    image, _, render_ok = _render_plantuml_jar(
        plantuml_code=sanitize_plantuml(fixture, "gantt"),
        status_msg="test render",
    )

    assert render_ok is True
    assert image is not None
