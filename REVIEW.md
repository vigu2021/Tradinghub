# Code review

These rules apply to every review. What to check on each side is in `backend/REVIEW.md` and
`frontend/REVIEW.md`.

## Evidence

- Report a finding only if you can quote the line that causes it and describe a concrete failure.
- Report it only if the author would fix it once they knew about it. If nothing qualifies, say
  "No findings".
- Check for a guard on the path, such as a filter, constraint or handler, before reporting a
  missing one.
- When reviewing a change, list problems it did not introduce separately as pre-existing. They do
  not affect the verdict. This does not apply when reviewing the whole codebase.
- Mark each finding Verified (you ran it or traced every step) or Unverified (say what was not
  run). Drop anything you disproved, and list it in one line.

## Project assumptions

- Solo project, nothing deployed. Rank a problem by what is true today, and name the scale or event
  that would make it worse.
- Do not suggest safeguards that have no effect on today's code paths.
- Other users' rows return 404, never 403.
- Login rate limiting is deliberately naive: every attempt counts for a fixed window.
- Rules about what is allowed belong in services. Well-formedness belongs in schemas.

A finding that contradicts one of these goes under Challenged assumptions and does not affect
the verdict.

## Design and complexity

Check these before the details, since they are the most expensive to change later.

- **Design:** the change fits how the system is built, and each piece is in the right place.
- **Complexity:** flag anything more complicated than the problem needs, including code for future
  needs nobody has yet. Say what to delete or simplify.

A design or complexity finding does not need a failure. Quote the lines and say what to move, delete
or simplify.

## Readability

Review readability as carefully as behaviour. A reader should understand the code on first read,
without tracing it or asking the author.

- **Names show intent:** functions, variables and types are self-descriptive. A function's name says
  what it does and a value's name says what it is for, so the code explains itself without a
  comment. Flag vague names such as `data`, `result`, `info`, `item`, `flag` and `handle`.
- **No abbreviations:** use full words, as listed under Naming in `CONVENTIONS.md`.
- **Names and docs tell the truth:** a name or docstring that no longer matches the code is a Medium
  finding, because it misleads the next change.
- **Code reads top to bottom:** flag deep nesting, clever one-liners, unexplained values, and any
  function that needs a comment to follow what it does.

A readability finding does not need a failure. Quote the line, say what a reader would misread or
have to work out, and give the exact replacement. Name the replacement or drop the finding.

## Severity

| Severity | Test |
|---|---|
| Critical | Normal use can lose data or expose another user's data |
| High | A plausible failure breaks a promise the system makes |
| Medium | A user can trigger wrong behaviour, with no lasting damage |
| Low | Real, but rare or cosmetic |

## Report

Start with a verdict: **Fix before commit** if there is a Verified Critical or High finding,
otherwise **OK to commit**. Then report in this order: what was read and run, counts (candidates,
verified, unverified, dropped), findings by severity, readability, pre-existing, unverified
questions, challenged assumptions, dropped.

Leave formatting to ruff and CI. Migrations are auto-generated, so do not review their style.
