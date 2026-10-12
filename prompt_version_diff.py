#!/usr/bin/env python3
"""prompt-version-diff: structured diff between two versions of a prompt.

Splits prompts into sections (instruction / examples / constraints / other),
matches sections across versions, grades each change by severity, and emits
semantic risk annotations (e.g. "constraint removed", "variables changed").
Pure standard library. Deterministic. No model calls.
"""
import argparse
import difflib
import json
import re
import sys

SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}
CLASS_SEVERITY = {"constraints": "high", "instruction": "medium", "examples": "low", "other": "low"}

CONSTRAINT_WORDS = ("constraint", "must not", "never", "do not", "forbidden",
                    "rule", "limit", "format", "warning", "restriction",
                    "约束", "禁止", "不得", "不允许", "规则", "限制", "格式", "警告")
EXAMPLE_WORDS = ("example", "few-shot", "fewshot", "sample", "input:", "output:",
                 "示例", "例子", "样例", "输入：", "输出：")
INSTRUCTION_WORDS = ("instruction", "task", "you must", "you are", "step",
                     "goal", "objective", "role", "system", "act as",
                     "任务", "指令", "目标", "角色", "步骤", "你必须", "你是")
VAR_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class DiffError(Exception):
    """Raised for unreadable or malformed inputs."""


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise DiffError("cannot read %s: %s" % (path, exc))
    except UnicodeDecodeError:
        raise DiffError("%s is not valid UTF-8 text" % path)


def normalize(text, ignore_whitespace=False):
    if ignore_whitespace:
        return "\n".join(" ".join(line.split()) for line in text.splitlines())
    return text


def split_sections(text):
    """Split prompt text into sections on markdown-ish headings."""
    sections = []
    title, lines = "(preamble)", []
    start = 1
    for lineno, line in enumerate(text.splitlines(), 1):
        match = HEADING_RE.match(line)
        if match:
            if lines or title != "(preamble)":
                sections.append({"title": title, "body": "\n".join(lines).strip(), "line": start})
            title, start, lines = match.group(2), lineno, []
        else:
            lines.append(line)
    sections.append({"title": title, "body": "\n".join(lines).strip(), "line": start})
    return sections


def classify(section):
    """Classify a section as instruction / examples / constraints / other."""
    hay = (section["title"] + "\n" + section["body"][:400]).lower()
    if any(w in hay for w in CONSTRAINT_WORDS):
        return "constraints"
    if any(w in hay for w in EXAMPLE_WORDS):
        return "examples"
    if any(w in hay for w in INSTRUCTION_WORDS):
        return "instruction"
    return "other"


def variables_of(text):
    return set(VAR_RE.findall(text))


def analyze(old_text, new_text, ignore_whitespace=False):
    old_text = normalize(old_text, ignore_whitespace)
    new_text = normalize(new_text, ignore_whitespace)
    old_sections = split_sections(old_text)
    new_sections = split_sections(new_text)
    old_by_title = {s["title"]: s for s in old_sections}
    new_by_title = {s["title"]: s for s in new_sections}

    changes, risks = [], []
    for title, section in new_by_title.items():
        cls = classify(section)
        if title not in old_by_title:
            changes.append({"type": "section_added", "section": title, "class": cls,
                            "severity": CLASS_SEVERITY[cls]})
            continue
        old_body = old_by_title[title]["body"]
        if old_body == section["body"]:
            continue
        ratio = difflib.SequenceMatcher(None, old_body, section["body"]).ratio()
        changes.append({"type": "section_modified", "section": title, "class": cls,
                        "severity": CLASS_SEVERITY[cls], "similarity": round(ratio, 3)})
        if cls == "constraints":
            risks.append({"risk": "constraint text changed", "section": title,
                          "detail": "a constraint section was edited; verify the restriction still holds"})
    for title, section in old_by_title.items():
        cls = classify(section)
        if title not in new_by_title:
            changes.append({"type": "section_removed", "section": title, "class": cls,
                            "severity": CLASS_SEVERITY[cls]})
            if cls == "constraints":
                risks.append({"risk": "constraint removed", "section": title,
                              "detail": "the new prompt no longer contains this constraint section"})

    old_vars, new_vars = variables_of(old_text), variables_of(new_text)
    added_vars, removed_vars = new_vars - old_vars, old_vars - new_vars
    if added_vars:
        risks.append({"risk": "variables added", "detail": sorted(added_vars)})
    if removed_vars:
        risks.append({"risk": "variables removed", "detail": sorted(removed_vars)})

    max_severity = "none"
    for change in changes:
        if SEVERITY_ORDER[change["severity"]] > SEVERITY_ORDER[max_severity]:
            max_severity = change["severity"]
    return {
        "old_sections": len(old_sections),
        "new_sections": len(new_sections),
        "changes": changes,
        "risks": risks,
        "max_severity": max_severity,
    }


def format_report(report, old_path, new_path):
    lines = ["prompt-version-diff: %s -> %s" % (old_path, new_path),
             "sections: %d -> %d, changes: %d, max severity: %s" % (
                 report["old_sections"], report["new_sections"],
                 len(report["changes"]), report["max_severity"])]
    for change in report["changes"]:
        lines.append("  [%s] %s: %s" % (change["severity"], change["type"], change["section"]))
    for risk in report["risks"]:
        lines.append("  RISK %s (%s)" % (risk["risk"], risk.get("section", ",".join(
            risk["detail"]) if isinstance(risk["detail"], list) else "")))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="prompt-version-diff", description=__doc__)
    parser.add_argument("old", help="old prompt file")
    parser.add_argument("new", help="new prompt file")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--ignore-whitespace", action="store_true",
                        help="collapse intra-line whitespace before comparing")
    parser.add_argument("--fail-on", default="high", choices=["none", "low", "medium", "high"],
                        help="exit 1 when max severity reaches this level")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse rejects bad args; return code instead of raising
        return int(exc.code) if exc.code else 0
    try:
        report = analyze(read_text(args.old), read_text(args.new),
                         ignore_whitespace=args.ignore_whitespace)
    except DiffError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_report(report, args.old, args.new))
    if args.fail_on != "none" and SEVERITY_ORDER[report["max_severity"]] >= SEVERITY_ORDER[args.fail_on]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
