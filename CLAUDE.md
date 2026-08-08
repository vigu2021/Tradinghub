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

This overrides the superpowers default of `docs/superpowers/specs/`. Do not create that directory.

## Who writes the code

Vignesh writes the implementation. Claude designs, plans, explains, and reviews. Write
implementation code only when explicitly handed a specific piece, and only that piece.

## Commits

Use the `safe-commit` skill. No Claude attribution in commit messages — no `Co-Authored-By`, no
"Generated with Claude Code".

## Slice order

1. Auth + skeleton — hand-rolled sessions, no email or OAuth
2. Trade journal CRUD
3. Binance read-only fill import
4. Charting + dashboard
5. Terraform on AWS

Each slice gets its own `plans/` folder with a design and a plan before any code is written.
