# Tradinghub

Multi-user trading journal. Built in ordered slices, primarily to learn FastAPI, Next.js, Postgres,
and Terraform on AWS in depth.

## Planning documents

All specs and plans live under `plans/`, nested by date then feature:

```
plans/
└── 2026-08-08/
    └── auth-skeleton/
        ├── spec.md    # what we're building and why
        └── plan.md    # the implementation plan: ordered steps
```

This overrides the superpowers defaults of `docs/superpowers/specs/` and `docs/superpowers/plans/`.
Do not create a `docs/` directory for planning material.

## Who writes the code

Vignesh writes the implementation. Claude designs, plans, explains, and reviews. Write
implementation code only when explicitly handed a specific piece, and only that piece.

## Commits

Use the `safe-commit` skill. No Claude attribution in commit messages — no `Co-Authored-By`, no
"Generated with Claude Code".

`safe-commit` treats `main` as a protected branch. This is a solo project with nothing deployed, so
committing directly to `main` is the accepted convention here — proceed rather than asking each
time. Revisit if collaborators or a deployed environment appear.

## Slice order

1. Auth + skeleton — hand-rolled sessions, no email or OAuth
2. Trade journal CRUD
3. Binance read-only fill import
4. Charting + dashboard
5. Terraform on AWS

Each slice gets its own `plans/` folder containing a `spec.md` and a `plan.md`, both written and
approved before any code.
