# ALIGNMENT (R13 design alignment — 16 items)

Repo: prompt-version-diff · as of 2026-10-11

1. Name matches design JSON: YES — `prompt-version-diff` == design repos[].name.
2. Mechanism matches design: YES — design mechanism "两版提示词的结构化 diff（指令段/示例段/约束段分级 + 语义风险标注）" is implemented as section split → class grading → risk annotations (prompt_version_diff.py).
3. Pure standard library: YES — imports are argparse, difflib, json, re, sys only.
4. CLI entry via argparse: YES — flags --json/--ignore-whitespace/--fail-on.
5. self_test.py runs standalone: YES — `python self_test.py`.
6. ≥40 self tests, three categories: YES — 46 tests: 19 functional, 5 exception-path, 12 extreme-edge, 10 CLI/behavior (v0.1.1 after round 2).
7. Final output line `SUMMARY: PASS n/n`: YES — verified by execution.
8. Edge coverage (empty/oversize/corrupt/unicode/nested): YES — empty files; 50k-char prompt; invalid UTF-8; unicode/CJK/emoji bodies; 40-heading deep structure; CRLF.
9. README first paragraph ≤60 words: YES — 52 words (counted manually).
10. README sections complete: YES — Problem / How it works / Quickstart (timed, repro) / Why not X / Minimal Fallback / Design Trade-offs / Limits & Second-order Effects / FAQ incl. When NOT to use / Core Assumptions (4) / Confidence / as of 2026-10-11.
11. why-not-X ≥3 alternatives incl. real anchors: YES — anchor openclaw-mcp-vps/prompt-version-diff-tool (0★) + git diff + LLM-based diff rows with one-layer differences.
12. LICENSE MIT "zhengming contributors": YES — no real names.
13. CHANGELOG v0.1.0 → v0.1.1: YES — both entries with revision trail.
14. Zero secrets / zero real names: YES — contact only hcac4735@agent.qq.com.
15. No >50-char anchor copying; numbers disciplined: YES — anchor usage is name+stars+difference only; timing [measured] with repro command.
16. Two content iterations, round-2 ≥20% improvement, tests re-run green: YES — round 2 raised tests 38→46 (+21.1%) and documented language limits; re-run PASS 46/46.
