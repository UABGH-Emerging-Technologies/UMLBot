"""Unit tests for the pure Gantt planning helpers."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from UMLBot.utils.gantt_planning import (
    Quarter,
    check_gantt_plan,
    extract_max_quarters,
    extract_start_date,
    plan_total_days,
    quarter_table,
    style_gantt,
    wants_detailed_plan,
)


class TestExtractStartDate:
    """Start dates are only read from explicit start phrases."""

    def test_iso_start_phrase(self) -> None:
        assert extract_start_date("The project starts 2027-07-01.") == date(2027, 7, 1)

    def test_slash_start_phrase(self) -> None:
        assert extract_start_date("Work starts 2027/07/01") == date(2027, 7, 1)

    def test_month_year_phrase(self) -> None:
        assert extract_start_date("starting July 2027") == date(2027, 7, 1)

    def test_month_abbrev_year_phrase(self) -> None:
        assert extract_start_date("starting Jul 2027") == date(2027, 7, 1)

    def test_month_day_year_phrase(self) -> None:
        assert extract_start_date("begins July 1, 2027") == date(2027, 7, 1)

    def test_day_month_year_phrase(self) -> None:
        assert extract_start_date("commencing 1 July 2027") == date(2027, 7, 1)

    def test_mm_yyyy_phrase(self) -> None:
        assert extract_start_date("kick off 07/2027") == date(2027, 7, 1)

    def test_quarter_phrase(self) -> None:
        assert extract_start_date("award date Q3 2027") == date(2027, 7, 1)

    def test_funded_from_phrase(self) -> None:
        assert extract_start_date("funded from 2027-07-01") == date(2027, 7, 1)

    def test_kickoff_single_word(self) -> None:
        assert extract_start_date("kickoff 2027-07-01") == date(2027, 7, 1)

    def test_incidental_dates_only_returns_none(self) -> None:
        assert extract_start_date("The database was published in 2019 and built 2021-03.") is None

    def test_earlier_unrelated_date_ignored(self) -> None:
        text = "Published 2019-01-01. The project starts 2027-07-01."
        assert extract_start_date(text) == date(2027, 7, 1)

    def test_ui_wrapped_request_limits_scope(self) -> None:
        description = (
            "You are an expert Gantt assistant.\n\n"
            "Latest user request:\n"
            "Plan starting July 2027\n\n"
            "Existing PlantUML diagram (dates such as 2019-01-01 are irrelevant):\n"
            "@startgantt\n@endgantt"
        )
        assert extract_start_date(description) == date(2027, 7, 1)

    def test_invalid_date_returns_none(self) -> None:
        assert extract_start_date("project starts 2027-13-45") is None

    def test_quarter_variants(self) -> None:
        assert extract_start_date("start Q1 2028") == date(2028, 1, 1)
        assert extract_start_date("start Q2 2028") == date(2028, 4, 1)
        assert extract_start_date("start Q4 2028") == date(2028, 10, 1)


class TestQuarterTable:
    """Quarter tables start with a partial first quarter when needed."""

    def test_calendar_quarter_start(self) -> None:
        rows = quarter_table(date(2027, 7, 1), 4)
        assert rows[0] == Quarter("Y1Q1", date(2027, 7, 1), date(2027, 9, 30))
        assert rows[1] == Quarter("Y1Q2", date(2027, 10, 1), date(2027, 12, 31))
        assert rows[2] == Quarter("Y1Q3", date(2028, 1, 1), date(2028, 3, 31))
        assert rows[3] == Quarter("Y1Q4", date(2028, 4, 1), date(2028, 6, 30))

    def test_mid_quarter_start_is_partial(self) -> None:
        rows = quarter_table(date(2027, 8, 15), 4)
        assert rows[0] == Quarter("Y1Q1", date(2027, 8, 15), date(2027, 9, 30))
        assert rows[1] == Quarter("Y1Q2", date(2027, 10, 1), date(2027, 12, 31))

    def test_labels_span_five_years(self) -> None:
        rows = quarter_table(date(2027, 7, 1), 20)
        assert rows[0].label == "Y1Q1"
        assert rows[19].label == "Y5Q4"

    def test_brute_force_contiguous_calendar_quarters(self) -> None:
        for year in range(2024, 2040):
            for quarter in range(1, 5):
                start = date(year, (quarter - 1) * 3 + 1, 1)
                rows = quarter_table(start, 20)
                assert len(rows) == 20
                for index, row in enumerate(rows):
                    if index > 0:
                        assert row.start == rows[index - 1].end + timedelta(days=1)
                    assert row.start.month in (1, 4, 7, 10)
                    assert row.start.day == 1
                    assert row.end.month in (3, 6, 9, 12)
                    expected_end = date(
                        row.end.year,
                        row.end.month,
                        calendar.monthrange(row.end.year, row.end.month)[1],
                    )
                    assert row.end == expected_end

    def test_leap_year_first_quarter_end(self) -> None:
        assert quarter_table(date(2028, 1, 1), 1)[0].end == date(2028, 3, 31)

    def test_year_rollover(self) -> None:
        rows = quarter_table(date(2027, 10, 1), 2)
        assert rows[0].end == date(2027, 12, 31)
        assert rows[1].start == date(2028, 1, 1)


class TestExtractMaxQuarters:
    """Explicit lengths are preferred over mechanism names."""

    def test_r21(self) -> None:
        assert extract_max_quarters("This is an R21 project.") == 8

    def test_r01(self) -> None:
        assert extract_max_quarters("Funded by R01.") == 20

    def test_two_year_plan(self) -> None:
        assert extract_max_quarters("a 2-year plan") == 8

    def test_spanning_two_years(self) -> None:
        assert extract_max_quarters("spanning 2 years") == 8

    def test_over_two_yr(self) -> None:
        assert extract_max_quarters("a plan over 2 yr") == 8

    def test_twenty_four_month_project(self) -> None:
        assert extract_max_quarters("a 24-month project") == 8

    def test_for_three_quarters(self) -> None:
        assert extract_max_quarters("plan for 3 quarters") == 3

    def test_clinical_durations_are_not_plan_lengths(self) -> None:
        # Real grant text: outcome windows must not cap the chart.
        assert extract_max_quarters("Secondary outcome is 1-year mortality.") is None
        assert extract_max_quarters("Patients have a 12-month follow-up.") is None
        assert extract_max_quarters("5-year survival is poor.") is None

    def test_mechanism_wins_over_clinical_duration(self) -> None:
        assert extract_max_quarters("This R21 studies 1-year mortality.") == 8

    def test_explicit_length_beats_mechanism(self) -> None:
        assert extract_max_quarters("3-year R01") == 12

    def test_none_when_absent(self) -> None:
        assert extract_max_quarters("Build a plan with several work packages.") is None

    def test_only_searches_user_request_section(self) -> None:
        description = (
            "Existing chart mentions R01.\n\n"
            "Latest user request:\n"
            "A short plan with no stated length.\n\n"
            "Recent conversation:\nR21 discussion"
        )
        assert extract_max_quarters(description) is None


class TestCheckGanttPlan:
    """The plan checker reports concrete, human-readable problems."""

    def test_undated_code_with_calendar_date(self) -> None:
        code = "@startgantt\n" "[A] starts 2027-01-01\n" "[A] ends 2027-02-01\n" "@endgantt"
        problems = check_gantt_plan(code, None, None, None)
        assert problems
        assert any("no start date" in problem for problem in problems)

    def test_undated_project_starts_line(self) -> None:
        code = "@startgantt\nProject starts 2027-01-01\n@endgantt"
        problems = check_gantt_plan(code, None, None, None)
        assert problems

    def test_undated_clean_code(self) -> None:
        code = (
            "@startgantt\n"
            "printscale weekly with week numbering from 1 zoom 0.5\n"
            "[A] starts D+0\n"
            "[A] ends D+90\n"
            "@endgantt"
        )
        assert check_gantt_plan(code, None, None, None) == []

    def test_dated_date_not_in_table(self) -> None:
        start = date(2027, 7, 1)
        quarters = quarter_table(start, 20)
        code = (
            "@startgantt\n"
            "Project starts 2027-07-01\n"
            "[A] starts 2027-08-15\n"
            "[A] ends 2027-09-30\n"
            "@endgantt"
        )
        problems = check_gantt_plan(code, start, quarters, None)
        assert any("2027-08-15" in problem for problem in problems)

    def test_dated_clean_code(self) -> None:
        start = date(2027, 7, 1)
        quarters = quarter_table(start, 20)
        code = (
            "@startgantt\n"
            "Project starts 2027-07-01\n"
            "[A] starts 2027-07-01\n"
            "[A] ends 2027-09-30\n"
            "[B] starts 2027-10-01\n"
            "[B] ends 2027-12-31\n"
            "@endgantt"
        )
        assert check_gantt_plan(code, start, quarters, None) == []

    def test_label_typo_detected(self) -> None:
        code = (
            "@startgantt\n"
            "[Early-warning evaluation] starts D+0\n"
            "[Early warning evaluation] ends D+90\n"
            "@endgantt"
        )
        problems = check_gantt_plan(code, None, None, None)
        assert any("Early-warning evaluation" in problem for problem in problems)

    def test_dated_dependency_violation(self) -> None:
        start = date(2027, 7, 1)
        quarters = quarter_table(start, 20)
        code = (
            "@startgantt\n"
            "Project starts 2027-07-01\n"
            "[A] starts 2027-07-01\n"
            "[A] ends 2027-09-30\n"
            "[B] starts 2027-07-01\n"
            "[B] ends 2027-12-31\n"
            "[A] -> [B]\n"
            "@endgantt"
        )
        problems = check_gantt_plan(code, start, quarters, None)
        assert any("starts before" in problem for problem in problems)

    def test_undated_dependency_violation(self) -> None:
        code = (
            "@startgantt\n"
            "[A] starts D+0\n"
            "[A] ends D+90\n"
            "[B] starts D+10\n"
            "[B] ends D+100\n"
            "[A] -> [B]\n"
            "@endgantt"
        )
        problems = check_gantt_plan(code, None, None, None)
        assert any("starts before" in problem for problem in problems)

    def test_starts_at_end_dependency_is_ok(self) -> None:
        code = (
            "@startgantt\n"
            "[A] starts D+0\n"
            "[A] ends D+90\n"
            "[B] starts at [A]'s end\n"
            "[B] ends D+180\n"
            "@endgantt"
        )
        assert check_gantt_plan(code, None, None, None) == []

    def test_span_over_max_dated(self) -> None:
        start = date(2027, 7, 1)
        quarters = quarter_table(start, 20)
        code = (
            "@startgantt\n"
            "Project starts 2027-07-01\n"
            "[A] starts 2027-07-01\n"
            "[A] ends 2027-12-31\n"
            "@endgantt"
        )
        problems = check_gantt_plan(code, start, quarters, 1)
        assert any("past the requested" in problem for problem in problems)

    def test_span_over_max_undated(self) -> None:
        code = "@startgantt\n[A] starts D+0\n[A] ends D+200\n@endgantt"
        problems = check_gantt_plan(code, None, None, 1)
        assert any("past the requested" in problem for problem in problems)

    def test_unknown_task_detected(self) -> None:
        code = "@startgantt\n" "[A] starts D+0\n" "[A] ends D+90\n" "[A] -> [Ghost]\n" "@endgantt"
        problems = check_gantt_plan(code, None, None, None)
        assert any("Unknown task 'Ghost'" in problem for problem in problems)

    def test_garbage_returns_empty_without_raising(self) -> None:
        assert check_gantt_plan("!!! not a gantt @@@ ###", None, None, None) == []
        assert check_gantt_plan("", date(2027, 7, 1), quarter_table(date(2027, 7, 1)), 2) == []


class TestReviewRegressions:
    """Defects found in review, pinned so they cannot return."""

    def test_dependency_starting_on_prerequisite_end_day_is_flagged_dated(self) -> None:
        code = (
            "@startgantt\nProject starts 2027-07-01\n[A] starts 2027-07-01\n[A] ends 2027-12-31\n"
            "[B] starts 2027-12-31\n[B] ends 2028-06-30\n[A] -> [B]\n@endgantt"
        )
        start = date(2027, 7, 1)
        assert check_gantt_plan(code, start, quarter_table(start), None) == [
            "Task 'B' starts before 'A' ends"
        ]

    def test_dependency_starting_next_day_is_ok_dated(self) -> None:
        code = (
            "@startgantt\nProject starts 2027-07-01\n[A] starts 2027-07-01\n[A] ends 2027-12-31\n"
            "[B] starts 2028-01-01\n[B] ends 2028-06-30\n[A] -> [B]\n@endgantt"
        )
        start = date(2027, 7, 1)
        assert check_gantt_plan(code, start, quarter_table(start), None) == []

    def test_dependency_starting_on_prerequisite_end_day_is_flagged_undated(self) -> None:
        code = "@startgantt\n[A] starts D+0\n[A] ends D+90\n[B] starts D+90\n[B] ends D+181\n[A] -> [B]\n@endgantt"
        assert check_gantt_plan(code, None, None, None) == ["Task 'B' starts before 'A' ends"]

    def test_bare_year_flagged_when_undated(self) -> None:
        code = "@startgantt\ntitle Plan 2027\n[A] starts D+0\n[A] ends D+90\n@endgantt"
        assert check_gantt_plan(code, None, None, None) == [
            "Year 2027 used but the request gave no start date"
        ]

    def test_day_offset_is_not_mistaken_for_a_year(self) -> None:
        code = "@startgantt\n[A] starts D+0\n[A] ends D+2027\n@endgantt"
        assert check_gantt_plan(code, None, None, None) == []

    def test_check_dates_false_skips_date_allowlist(self) -> None:
        code = "@startgantt\nProject starts 2027-07-01\n[A] starts 2027-07-15\n[A] ends 2027-08-20\n@endgantt"
        start = date(2027, 7, 1)
        assert check_gantt_plan(code, start, quarter_table(start), None, check_dates=False) == []


class TestPlanTotalDays:
    """The plan span is measured from task start/end lines."""

    def test_dated_span_in_days(self) -> None:
        code = (
            "@startgantt\nProject starts 2027-07-01\n"
            "[A] starts 2027-07-01\n[A] ends 2027-09-30\n@endgantt"
        )
        assert plan_total_days(code) == 92

    def test_undated_span_in_days(self) -> None:
        code = "@startgantt\n[A] starts D+0\n[A] ends D+90\n@endgantt"
        assert plan_total_days(code) == 91

    def test_earliest_start_and_latest_end(self) -> None:
        code = (
            "@startgantt\n"
            "[A] starts D+10\n[A] ends D+20\n"
            "[B] starts D+0\n[B] ends D+100\n"
            "@endgantt"
        )
        assert plan_total_days(code) == 101

    def test_none_without_tasks(self) -> None:
        assert plan_total_days("@startgantt\nprintscale monthly\n@endgantt") is None

    def test_none_for_unparseable_lines(self) -> None:
        assert plan_total_days("[A] starts at [B]'s end\n@endgantt") is None


class TestStyleGanttScale:
    """The axis directive is chosen from the chart's dating and span."""

    def test_dated_short_plan_uses_weekly(self) -> None:
        code = (
            "@startgantt\nProject starts 2027-07-01\n"
            "[A] starts 2027-07-01\n[A] ends 2027-09-30\n@endgantt"
        )
        styled = style_gantt(code, dated=True, total_days=plan_total_days(code))
        assert "printscale weekly zoom 2" in styled
        assert "printscale quarterly" not in styled

    def test_dated_long_plan_uses_quarterly(self) -> None:
        code = (
            "@startgantt\nProject starts 2027-07-01\n"
            "[A] starts 2027-07-01\n[A] ends 2029-06-30\n@endgantt"
        )
        styled = style_gantt(code, dated=True, total_days=plan_total_days(code))
        assert "printscale quarterly zoom 2" in styled

    def test_undated_plan_uses_weekly_axis(self) -> None:
        code = "@startgantt\n[A] starts D+0\n[A] ends D+90\n@endgantt"
        styled = style_gantt(code, dated=False, total_days=plan_total_days(code))
        assert "printscale weekly with week numbering from 1 zoom 2" in styled
        assert "zoom 0.25" not in styled

    def test_undated_long_plan_never_uses_calendar_scale(self) -> None:
        # Undated, PlantUML draws monthly/quarterly as one column per day, which
        # is a solid grey block for a two-year plan; a numbered weekly axis is used.
        code = "@startgantt\n[A] starts D+0\n[A] ends D+727\n@endgantt"
        styled = style_gantt(code, dated=False, total_days=plan_total_days(code))
        assert "printscale weekly with week numbering from 1 zoom 0.5" in styled
        assert "quarterly" not in styled and "monthly" not in styled

    def test_ai_zoom_clause_is_replaced(self) -> None:
        code = (
            "@startgantt\n"
            "printscale weekly with week numbering from 1 zoom 0.25\n"
            "[A] starts D+0\n[A] ends D+90\n@endgantt"
        )
        styled = style_gantt(code, dated=False, total_days=plan_total_days(code))
        assert "zoom 0.25" not in styled
        assert "printscale weekly with week numbering from 1 zoom 2" in styled

    def test_very_short_plan_uses_daily(self) -> None:
        code = (
            "@startgantt\nProject starts 2027-07-01\n"
            "[A] starts 2027-07-01 and lasts 3 days\n@endgantt"
        )
        styled = style_gantt(code, dated=True, total_days=plan_total_days(code))
        assert "printscale daily zoom 2" in styled

    def test_month_long_plan_uses_daily(self) -> None:
        code = (
            "@startgantt\nProject starts 2027-07-01\n"
            "[A] starts 2027-07-01 and lasts 15 days\n@endgantt"
        )
        styled = style_gantt(code, dated=True, total_days=plan_total_days(code))
        assert "printscale daily zoom 2" in styled

    def test_no_span_uses_numbered_weekly_axis(self) -> None:
        code = "@startgantt\n[A] starts at [B]'s end\n@endgantt"
        styled = style_gantt(code, dated=False, total_days=plan_total_days(code))
        assert "printscale weekly with week numbering from 1 zoom 2" in styled


class TestStyleGanttHides:
    """Hide directives are inserted once and the result is idempotent."""

    def test_hide_lines_inserted_once(self) -> None:
        code = "@startgantt\n[A] starts D+0\n[A] ends D+90\n@endgantt"
        styled = style_gantt(code, dated=False, total_days=91)
        assert styled.count("hide column start") == 1
        assert styled.count("hide column end") == 1
        assert styled.count("hide column duration") == 1
        assert styled.count("hide footbox") == 1

    def test_idempotent_on_second_call(self) -> None:
        code = (
            "@startgantt\nProject starts 2027-07-01\n"
            "-- Aim 1 --\n[A] starts 2027-07-01\n[A] ends 2027-09-30\n@endgantt"
        )
        once = style_gantt(code, dated=True, total_days=plan_total_days(code))
        twice = style_gantt(once, dated=True, total_days=plan_total_days(once))
        assert twice == once

    def test_never_raises_on_garbage(self) -> None:
        assert style_gantt("not plantuml at all", dated=True, total_days=None) == (
            "not plantuml at all"
        )


class TestStyleGanttColours:
    """Each section gets one palette colour; milestones get none."""

    def _three_sections(self) -> str:
        return (
            "@startgantt\n"
            "[A] starts D+0\n[A] ends D+90\n"
            "-- Section one --\n"
            "[B] starts D+0\n[B] ends D+90\n"
            "-- Section two --\n"
            "[C] starts D+0\n[C] ends D+90\n"
            "[M done] happens at [C]'s end\n"
            "@endgantt"
        )

    def test_sections_cycle_palette(self) -> None:
        styled = style_gantt(self._three_sections(), dated=False, total_days=91)
        assert "[A] is colored in LightSteelBlue" in styled
        assert "[B] is colored in Moccasin" in styled
        assert "[C] is colored in Thistle" in styled

    def test_chart_starting_with_a_separator_uses_first_colour(self) -> None:
        # Real AI output opens with "-- Aim 1 --"; Aim 1 must get the first colour.
        code = (
            "@startgantt\n"
            "-- Aim 1 --\n[A] starts D+0\n[A] ends D+90\n"
            "-- Aim 2 --\n[B] starts D+0\n[B] ends D+90\n"
            "-- Dissemination --\n[C] starts D+91\n[C] ends D+181\n"
            "@endgantt"
        )
        styled = style_gantt(code, dated=False, total_days=182)
        assert "[A] is colored in LightSteelBlue" in styled
        assert "[B] is colored in Moccasin" in styled
        assert "[C] is colored in Thistle" in styled

    def test_milestone_has_no_colour_line(self) -> None:
        styled = style_gantt(self._three_sections(), dated=False, total_days=91)
        assert "[M done] is colored in" not in styled

    def test_existing_colour_line_not_duplicated(self) -> None:
        code = (
            "@startgantt\n"
            "[A] is colored in PaleGreen\n"
            "[A] starts D+0\n[A] ends D+90\n"
            "@endgantt"
        )
        styled = style_gantt(code, dated=False, total_days=91)
        assert styled.count("[A] is colored in") == 1
        assert "[A] is colored in PaleGreen" in styled


class TestCheckGanttPlanMaxTasks:
    """Too many task bars are reported when a cap is given."""

    def test_too_many_tasks_reported(self) -> None:
        lines = ["@startgantt"]
        for index in range(11):
            lines.append(f"[T{index}] starts D+0")
            lines.append(f"[T{index}] ends D+10")
        lines.append("@endgantt")
        problems = check_gantt_plan("\n".join(lines), None, None, None, max_tasks=10)
        assert any("Too many tasks (11)" in problem for problem in problems)

    def test_under_cap_has_no_task_problem(self) -> None:
        code = "@startgantt\n[A] starts D+0\n[A] ends D+90\n@endgantt"
        assert check_gantt_plan(code, None, None, None, max_tasks=10) == []

    def test_presentation_lines_are_ignored(self) -> None:
        code = (
            "@startgantt\n"
            "hide column start\nhide column end\nhide column duration\nhide footbox\n"
            "printscale weekly with week numbering from 1 zoom 0.5\n"
            "[A] starts D+0\n[A] ends D+90\n[A] is colored in LightSteelBlue\n"
            "@endgantt"
        )
        assert check_gantt_plan(code, None, None, None, max_tasks=10) == []


class TestWantsDetailedPlan:
    """Only the user's request section decides whether detail is wanted."""

    def test_detailed_request(self) -> None:
        assert wants_detailed_plan("a detailed gantt") is True

    def test_plain_request_is_high_level(self) -> None:
        assert wants_detailed_plan("Plan the aims of this project") is False

    def test_detailed_only_in_context_is_ignored(self) -> None:
        description = (
            "Existing chart mentions a detailed plan.\n\n"
            "Latest user request:\n"
            "Plan the aims.\n\n"
            "Recent conversation:\nA detailed plan was requested."
        )
        assert wants_detailed_plan(description) is False


class TestHandEditedCode:
    """Code a person typed in the editor must be rendered as they wrote it."""

    _USER_EDIT = (
        "@startgantt\n"
        "hide footbox\n"
        "Project starts 2027-07-01\n"
        "printscale quarterly zoom 2\n"
        "-- Aim 1 --\n"
        "[Develop BHCI algorithm] as [DEV] requires 91 days\n"
        "[DEV] is colored in LightSteelBlue\n"
        "[Internal validation] as [IV] requires 182 days\n"
        "[IV] starts at [DEV]'s end\n"
        "[BHCI locked] happens at [IV]'s end\n"
        "-- Dissemination --\n"
        "[Aim 1 manuscript] as [M1] requires 91 days\n"
        "[M1] starts at [IV]'s end\n"
        "[M1] is colored in LightGray\n"
        "@endgantt"
    )

    def test_user_colours_are_kept_and_scale_is_code_owned(self) -> None:
        styled = style_gantt(
            self._USER_EDIT, dated=True, total_days=None, preserve_user_choices=True
        )
        assert "printscale weekly with week numbering from 1 zoom 2" in styled
        assert "printscale quarterly zoom 2" not in styled
        assert "[M1] is colored in LightGray" in styled
        assert styled.count("is colored in") == 2
        assert "hide column start" in styled

    def test_missing_scale_is_still_added_for_user_code(self) -> None:
        code = "@startgantt\nProject starts 2027-07-01\n[A] starts 2027-07-01\n[A] ends 2027-09-30\n@endgantt"
        styled = style_gantt(code, dated=True, total_days=92, preserve_user_choices=True)
        assert "printscale weekly zoom 2" in styled

    def test_alias_and_requires_syntax_passes_plan_check(self) -> None:
        start = date(2027, 7, 1)
        problems = check_gantt_plan(
            self._USER_EDIT, start, quarter_table(start), None, check_dates=False
        )
        assert problems == []

    def test_unknown_alias_is_still_reported(self) -> None:
        code = self._USER_EDIT.replace("[M1] starts at [IV]'s end", "[M1] starts at [IVX]'s end")
        start = date(2027, 7, 1)
        problems = check_gantt_plan(code, start, quarter_table(start), None, check_dates=False)
        assert problems == ["Unknown task 'IVX'"]
