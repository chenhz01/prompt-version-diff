# Changelog

## v0.1.2 (2026-10-12)

Round-13 fix pass (self_test rc=2 crash, 0 counted):

- fix: main() now catches the SystemExit raised by argparse on bad arguments
  and returns its code instead of propagating (crash made self_test exit 2
  before printing any summary)
- fix: --fail-on none now always exits 0 (previously any severity >= none
  returned 1, making the gate unusable as an off switch)
- fix: classification keywords extended with Chinese equivalents (任务/指令/
  目标/角色/步骤, 约束/禁止/不得/规则/限制/格式/警告, 示例/例子/样例/输入：/输出：)
  so Chinese instruction/constraint/example sections grade correctly
- tests added: empty-text split, non-constraint removal, directory read error,
  missing second CLI file, SystemExit-free bad-arg handling, heading-only
  prompts, duplicate titles, CRLF+ignore-whitespace, fail-on none gate
- self tests: 43/43 PASS (34 -> 43)


## v0.1.1 (2026-10-11)

Round-2 content iteration (self-review driven):

- test coverage: 38 -> 46 self tests (+21.1%), adding bad --fail-on rejection,
  CRLF equality, heading-level variation, emoji bodies, preamble severity and
  CLI JSON/gate checks
- documentation: README now states English-keyword classification limits for
  non-English prompts explicitly

## v0.1.0 (2026-10-11)

Initial release:

- section splitting on markdown headings with preamble handling
- classification: instruction / examples / constraints / other (keyword rules)
- severity grading: constraints=high, instruction=medium, examples/other=low
- risk annotations: constraint edited/removed, variables added/removed
- CLI: --json --ignore-whitespace --fail-on; exit 0/1/2 discipline
- self_test.py: 38 tests across functional / exception-path / extreme-edge
