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

Planning material goes here and nowhere else. Do not create a `docs/` directory for it.

## Code conventions

See `CONVENTIONS.md`.

## Who writes the code

Implementation is written by hand, not by Claude. Claude designs, plans, explains, and reviews.
Write implementation code only when explicitly handed a specific piece, and only that piece.

## Commits

Scan the staged diff for secrets before every commit. Commit messages are one line, plain, with no
tooling attribution of any kind.

Committing directly to `main` is fine here — solo project, nothing deployed. Revisit if
collaborators or a deployed environment appear.

## Slice order

1. Auth + skeleton — hand-rolled sessions, no email or OAuth
2. Trade journal CRUD
3. Binance read-only fill import
4. Charting + dashboard
5. Terraform on AWS

Each slice gets its own `plans/` folder containing a `spec.md` and a `plan.md`, both written and
approved before any code.
