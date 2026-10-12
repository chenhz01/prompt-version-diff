#!/usr/bin/env python3
"""Self-test for prompt-version-diff. Pure stdlib. Run: python self_test.py"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prompt_version_diff as pvd  # noqa: E402

TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def wf(content, name="f.txt"):
    d = tempfile.mkdtemp()
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return d, p


def expect_diff_error(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except pvd.DiffError:
        return
    raise AssertionError("expected DiffError")


# ---------------- functional unit tests ----------------

@test("split_single_preamble")
def _():
    assert pvd.split_sections("just text") == [
        {"title": "(preamble)", "body": "just text", "line": 1}]


@test("split_two_headings")
def _():
    s = pvd.split_sections("# Task\nDo X\n# Rules\nNo Y")
    assert [x["title"] for x in s] == ["Task", "Rules"]
    assert s[1]["body"] == "No Y"


@test("split_preamble_before_first_heading")
def _():
    s = pvd.split_sections("intro\n# A\nbody")
    assert s[0]["title"] == "(preamble)" and s[0]["body"] == "intro"
    assert s[1]["title"] == "A"


@test("classify_constraints_by_title")
def _():
    assert pvd.classify({"title": "Constraints", "body": ""}) == "constraints"


@test("classify_examples_by_body_keyword")
def _():
    assert pvd.classify({"title": "Stuff", "body": "Example: 1+1=2"}) == "examples"


@test("classify_instruction_default_for_task_words")
def _():
    assert pvd.classify({"title": "The Task", "body": "do things"}) == "instruction"


@test("classify_other_fallback")
def _():
    assert pvd.classify({"title": "Notes", "body": "random remark"}) == "other"


@test("variables_extracted")
def _():
    assert pvd.variables_of("{a} and {b_2} end {1bad}") == {"a", "b_2"}


@test("identical_prompt_no_changes")
def _():
    r = pvd.analyze("# T\nsame body", "# T\nsame body")
    assert r["changes"] == [] and r["max_severity"] == "none"


@test("constraint_modified_flags_high")
def _():
    r = pvd.analyze("# Constraints\nnever lie", "# Constraints\nnever lie ever")
    assert r["max_severity"] == "high"
    assert any(c["type"] == "section_modified" for c in r["changes"])


@test("constraint_removed_flags_risk")
def _():
    r = pvd.analyze("# Constraints\nno secrets\n# Other\nx", "# Other\nx")
    assert any(rk["risk"] == "constraint removed" for rk in r["risks"])
    assert r["max_severity"] == "high"


@test("examples_change_is_low")
def _():
    r = pvd.analyze("# Examples\nin: a out: b", "# Examples\nin: c out: d")
    assert r["max_severity"] == "low"


@test("instruction_change_is_medium")
def _():
    r = pvd.analyze("# Task\nsum numbers", "# Task\nmultiply numbers")
    assert r["max_severity"] == "medium"


@test("section_added_classified")
def _():
    r = pvd.analyze("# Task\ndo", "# Task\ndo\n# Constraints\nnone")
    added = [c for c in r["changes"] if c["type"] == "section_added"]
    assert len(added) == 1 and added[0]["class"] == "constraints"


@test("variables_added_risk")
def _():
    r = pvd.analyze("hi {a}", "hi {a} {new_var}")
    assert any(rk["risk"] == "variables added" and rk["detail"] == ["new_var"]
               for rk in r["risks"])


@test("variables_removed_risk")
def _():
    r = pvd.analyze("hi {a} {old}", "hi {a}")
    assert any(rk["risk"] == "variables removed" for rk in r["risks"])


@test("similarity_recorded_on_modify")
def _():
    r = pvd.analyze("# Task\nalpha", "# Task\nalpha beta")
    mod = [c for c in r["changes"] if c["type"] == "section_modified"][0]
    assert 0 < mod["similarity"] < 1


@test("format_report_includes_severity")
def _():
    r = pvd.analyze("# Task\na", "# Task\nb")
    text = pvd.format_report(r, "old.txt", "new.txt")
    assert "medium" in text and "old.txt -> new.txt" in text


@test("ignore_whitespace_makes_equal")
def _():
    r = pvd.analyze("# T\nhello   world", "# T\nhello world", ignore_whitespace=True)
    assert r["changes"] == []


@test("empty_text_single_preamble_empty_body")
def _():
    s = pvd.split_sections("")
    assert len(s) == 1 and s[0]["title"] == "(preamble)" and s[0]["body"] == ""


@test("non_constraint_removed_no_risk")
def _():
    r = pvd.analyze("# Notes\nstuff\n# Task\nx", "# Task\nx")
    assert any(c["type"] == "section_removed" and c["section"] == "Notes" for c in r["changes"])
    assert r["risks"] == []


# ---------------- exception-path tests ----------------

@test("missing_old_file_raises")
def _():
    expect_diff_error(pvd.read_text, os.path.join(tempfile.mkdtemp(), "no.txt"))


@test("invalid_utf8_raises")
def _():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "bin.txt")
    with open(p, "wb") as f:
        f.write(b"\xff\xfe\xfa")
    expect_diff_error(pvd.read_text, p)


@test("cli_missing_file_exit_2")
def _():
    code = pvd.main([os.path.join(tempfile.mkdtemp(), "x.txt"),
                     os.path.join(tempfile.mkdtemp(), "y.txt")])
    assert code == 2


@test("bad_failon_choice_rejected")
def _():
    d1, p1 = wf("a")
    d2, p2 = wf("a")
    try:
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            code = pvd.main([p1, p2, "--fail-on", "extreme"])
        assert code == 2
    finally:
        shutil.rmtree(d1), shutil.rmtree(d2)


@test("empty_files_no_changes")
def _():
    r = pvd.analyze("", "")
    assert r["changes"] == [] and r["risks"] == []


@test("read_directory_raises_diff_error")
def _():
    expect_diff_error(pvd.read_text, tempfile.mkdtemp())


@test("cli_missing_second_file_exit_2")
def _():
    d, p1 = wf("a")
    try:
        code = pvd.main([p1, os.path.join(d, "ghost.txt")])
        assert code == 2
    finally:
        shutil.rmtree(d)


@test("main_returns_instead_of_raising_on_bad_args")
def _():
    try:
        code = pvd.main(["--help-not-real-flag"])
    except SystemExit:
        raise AssertionError("main raised SystemExit instead of returning")
    assert code == 2


# ---------------- extreme-edge tests ----------------

@test("unicode_prompt_diff")
def _():
    r = pvd.analyze("# 任务\n总结内容", "# 任务\n总结全部内容")
    assert r["max_severity"] == "medium"


@test("long_prompt_50k")
def _():
    body = "line\n" * 10000
    r = pvd.analyze("# T\n" + body, "# T\n" + body)
    assert r["changes"] == []


@test("deeply_nested_headings")
def _():
    text = "".join("#" * min(i, 6) + " H%d\nbody\n" % i for i in range(1, 40))
    s = pvd.split_sections(text)
    assert len(s) == 39


@test("crlf_prompts_equal")
def _():
    r = pvd.analyze("# T\r\nline1\r\nline2", "# T\nline1\nline2")
    assert r["changes"] == []


@test("heading_level_variation_same_title")
def _():
    r = pvd.analyze("# Task\nx", "## Task\nx")
    assert r["changes"] == []


@test("emoji_and_marks_in_body")
def _():
    r = pvd.analyze("# T\nok 🚀✅", "# T\nok 🚀✅")
    assert r["changes"] == []


@test("preamble_change_is_low")
def _():
    r = pvd.analyze("free text v1", "free text v2")
    assert r["max_severity"] == "low"


@test("var_only_change_low_severity_but_risk")
def _():
    r = pvd.analyze("# Task\n{a}", "# Task\n{b}")
    assert r["max_severity"] == "medium"
    assert r["risks"]


@test("cli_json_output_parseable")
def _():
    d1, p1 = wf("# Task\na")
    d2, p2 = wf("# Task\nb")
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            assert pvd.main([p1, p2, "--json", "--fail-on", "none"]) == 0
        data = json.loads(buf.getvalue())
        assert data["max_severity"] == "medium"
    finally:
        shutil.rmtree(d1), shutil.rmtree(d2)


@test("cli_fail_on_low_exit_1")
def _():
    d1, p1 = wf("# Examples\nx")
    d2, p2 = wf("# Examples\ny")
    try:
        assert pvd.main([p1, p2]) == 0          # default fail-on=high
        assert pvd.main([p1, p2, "--fail-on", "low"]) == 1
    finally:
        shutil.rmtree(d1), shutil.rmtree(d2)


@test("only_headings_no_bodies_no_changes")
def _():
    r = pvd.analyze("# A\n# B\n# C", "# A\n# B\n# C")
    assert r["changes"] == [] and r["max_severity"] == "none"


@test("duplicate_titles_last_wins_no_crash")
def _():
    r = pvd.analyze("# T\none\n# T\ntwo", "# T\nthree")
    assert isinstance(r["max_severity"], str)


@test("ignore_whitespace_with_crlf_equal")
def _():
    r = pvd.analyze("# T\r\na   b\r\nc", "# T\na b\nc", ignore_whitespace=True)
    assert r["changes"] == []


@test("fail_on_none_always_exit_0")
def _():
    d1, p1 = wf("# Constraints\nold rule")
    d2, p2 = wf("# Constraints\nnew rule")
    try:
        assert pvd.main([p1, p2, "--fail-on", "none"]) == 0
    finally:
        shutil.rmtree(d1), shutil.rmtree(d2)


def main():
    passed = failed = 0
    for name, fn in TESTS:
        try:
            fn()
            passed += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print("FAIL %s: %r" % (name, exc))
    print("passed=%d failed=%d total=%d" % (passed, failed, passed + failed))
    print("SUMMARY: PASS %d/%d" % (passed, passed + failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
