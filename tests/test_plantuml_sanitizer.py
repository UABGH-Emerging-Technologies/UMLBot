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
def test_sanitized_fixture_renders_with_real_jar() -> None:
    from UMLBot.services.diagram_service import _render_plantuml_jar

    image, _, render_ok = _render_plantuml_jar(
        plantuml_code=sanitize_plantuml(GANTT_FIXTURE, "gantt"),
        status_msg="test render",
    )

    assert render_ok is True
    assert image is not None
