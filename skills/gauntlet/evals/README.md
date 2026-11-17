# Evaluating the gauntlet

The reviewer is judged on real output, by Joe, against the anti-goals in the design. The fixtures
here are small Rails diffs. Run the skill on each in a fresh Claude Code session (paste the diff as the
change under review, or apply it to a scratch branch), and read what it says.

## Fixtures and what a good review does

| Fixture | Planted | A good review |
| --- | --- | --- |
| `partial-transaction.diff` | A contract is created, then schedules are saved one by one with no transaction. A failing schedule leaves a committed contract. The only spec covers the happy path | Raises the partial failure **first**, as a question. Offers an alternative (one transaction around both writes, or a status field with a retry) and the trade-off. Notes the missing failing-schedule test as a detail |
| `let-in-spec.diff` | `let`, an explicit `subject`, a `before` hook and `reload` in a spec | Flags each as a non-blocking detail, citing Testing §3.3, §3.4 and §3.16, and says why (lazy and overridable, so hard to see where a value comes from). Does not push "one expectation per test" |
| `rubocop-only.diff` | Only a long line, a trailing comma and double quotes | **No findings.** A linter teaches these. Says so and posts nothing |
| `clean.diff` | Nothing. Injected clock, idempotent guard, AAA spec with factories | No findings, or at most one minor point. Must not invent a problem or guess at code the diff does not show |
| `detail-heavy.diff` | Working code with `data` used as a name in three places, vague `process` and `calc`, `qty`, and an unexplained constant `BUFFER` | Inline, non-blocking details. The repeated `data` is **one grouped comment**, not three. Asks what `BUFFER` is for. At most 2 design findings and 4 details (a 20-line diff), and no "nothing to change" remarks |

A design question about the service itself, grounded in what the diff shows (a retry creating a second
record, a notifier failing after the save), is acceptable on any fixture. A guess about code the diff
does not show is not.

## Intent check

Run `partial-transaction` once with a PR description that says "temporary spike". The partial-failure
finding must still be raised (correctness applies either way). Details that matter only for durable
code, such as the missing failure-path test, should soften.

## Standing checks (every run)

- At most 6 design findings and about 8 details; at most 2 and 4 when the diff is under about 60 changed lines.
- Nothing reported that needs no change ("naming looks fine", "nothing to change here").
- No point that depends on code the diff does not show, unless it names what would go wrong.
- Findings are questions, each with another way to do it and its trade-off (design findings).
- Weight is in plain words. No `issue:`, `nitpick:` or similar prefixes.
- Nothing is asserted without a file and line in the diff.
- Nothing is posted without Joe approving the exact text, and `--dry-run` comes first.
- The summary states the hack-or-built-to-stand assumption.
- No retired rule is enforced (spec-driven, `Spec:` footers).
- It stays under the cap, and does not bury the one important point.

## Reference PRs

Also run it on two or three past `westernmilling/contracto` PRs where Joe's real comments are the
reference. For each, compare: did it find what Joe found, in a similar voice, without the noise Joe
would not have written?

## Tuning

If Joe finds it too noisy or too quiet, adjust the caps in `SKILL.md` (section 6), the wording in
`lenses.md`, or the examples in `voice-examples.md`, then re-run the affected fixtures.
