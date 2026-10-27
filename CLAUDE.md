# Hay Logger

Django 5 app for tracking hay bales in a barn: deliveries (DEPOSIT), usage (WITHDRAW),
burn rates and a usage chart. One app, `log_app`. SQLite database at `db/db.sqlite3`.

## Commands

```bash
uv sync                           # dependencies into .venv (dev group: pytest, pytest-django, ruff, jamb)
uv run python manage.py runserver # local dev server
uv run pytest                     # all tests (pytest-django; config in pyproject.toml)
uv run pytest --jamb              # tests + requirements coverage summary (writes .jamb)
uv run jamb validate              # requirements tree: broken links, suspect links, unreviewed
uv run python manage.py makemigrations --check --dry-run   # models match migrations?
uv run ruff check --fix . && uv run ruff format .          # also run by pre-commit
uv add <pkg> / uv add --dev <pkg> # add a dependency (ask first); updates uv.lock
```

Dependencies are managed with uv (`pyproject.toml` `[project]` + `uv.lock`), not Poetry.
`[tool.uv] package = false`: the project itself isn't installed, only its dependencies.
The `upload` group (pandas, for `up_load/`) is opt-in: `uv sync --group upload`.

## Deployment

Push to `main` -> GitHub Actions runs `pytest`, then builds the image and pushes it to
Docker Hub `3ltreilly/hay-logger` -> the Synology server (`milhouse.local`) pulls it and runs
it with `db/` mounted as a volume. See `wip.sh` for the server commands. Pull requests to
`main` run the tests and build the image but never push it. On start the container runs
`migrate`, then gunicorn (WhiteNoise serves the static files `collectstatic` gathers at
build time).

Settings come from environment variables with local-development defaults: `DJANGO_DEBUG`
(on unless set; the Dockerfile sets it to 0) and `DJANGO_SECRET_KEY` (a throwaway default).
With debug off, settings refuse to load without a real key. The server's key is in an env
file on the Synology (`/volume1/docker/hay-logger/hay-logger.env`, passed with
`--env-file`), never in git or the image, which is public on Docker Hub.

CI installs from a clean environment (`uv sync --locked`), so it is the real test of
`uv.lock`. A local venv can hold packages the lock doesn't pin (e.g. an old `setuptools`) and
hide breakage; `rm -rf .venv && uv sync` gives you the same clean install.

## Requirements (jamb)

Requirements live as YAML in `reqs/`, traced to tests with the `jamb` pytest plugin.
Background and best practices: `requirements_chat.md`.

- **Hierarchy:** `PRJ` (root, ignored in tracing) -> `UN` user needs -> `SRS` software
  requirements. UN text is in the user's words and is approved by the user; SRS text says
  what the system does ("the dashboard shows…"), with a worked example in numbers.
- **Test markers go on SRS only** (`test_documents = ["SRS"]`):
  `@pytest.mark.requirement("SRS004")`. Never mark tests with UN IDs; tests reach UN through
  the SRS links. Only mark a test with a requirement it actually asserts; a page-loads smoke
  test doesn't cover "shows a blank".
- **Add items with the CLI** (`uv run jamb item add SRS --links UN003 --header … --text …`)
  so links and files are written correctly. Quote multi-line `text:` carefully; one bad
  YAML file makes `jamb validate` fail for the whole tree.
- **Reviews are the owner's/user's approval:** `jamb review mark` (an item's own text is
  approved) and `jamb review clear` (a child still fits its changed parent). Don't run
  either unless asked. Editing an item clears its review and makes its children's links
  suspect; that's intended.
- **UIDs are permanent.** Don't renumber (`jamb reorder`, `item add --before/--after`):
  approvals, emails and PRs quote them. Gaps are fine.
- **Grouping:** for now one SRS folder. Use custom YAML keys (e.g. `area: dashboard`; not
  part of the review hash) for cross-cutting views; split into per-area documents
  (own folder and prefix, add to `test_documents`) only when a folder gets hard to scan.
- **`jamb check` misses markers on `TestCase` methods** (reports SRS008 uncovered); trust
  `pytest --jamb`.
- Generated output (`.jamb`, `matrix.html`, `srs.html`, `all.html`) isn't source.
- Known gaps: SRS003 (horse-count pre-fill) has no test; the "blank" cases in SRS005/006
  are only smoke-tested.

## Gotchas

- **Migrations:** the production database has `log_app` migrations 0001–0008 applied
  (verified to match the local files). Never delete, rename or regenerate them. When a
  model changes, run `makemigrations` and commit the new file with the model change.
  The container applies new migrations to the production database on start, so a merge to
  `main` with a migration in it changes the only copy of the data. Back up
  `db/db.sqlite3` on the server before deploying one. 0009 (table rename), 0010
  (`Log.date` default) and 0011 (balance-correction logs, a data migration) are the first
  to go out this way.
- **Time zones:** `USE_TZ = True`. Use `django.utils.timezone.now()`, never
  `datetime.now()`. `log_app/tests.py` still builds naive dates (the RuntimeWarnings).
- **Totals come from the logs:** `BaleCount.current_total()` is deposits minus withdrawals.
  Migration 0011 added one "Balance correction" log per hay type (dated at its first log)
  so the logs match the old stored totals. The `BaleCount.total` column is no longer read or
  updated; it stays only until a later migration removes it (then also delete
  `BalanceCorrectionMigrationTests` in `tests.py`). The usage chart builds running totals
  from every log and only then trims to the requested date range.
- **Naming:** `BaleCount` is really a hay type (first/second cutting). It was renamed
  from the misspelled `BailCount` in migration 0009, so the old spelling remains only in
  migrations 0003–0008. Don't edit those files.
- **`log_app/test_bugs.py`:** the BUG tests have all been fixed and now act as regression
  tests; every test in the file must stay green.
- **Burn rates:** `burn_rate()` returns the real rate (0 when a hay type has no usage), not
  a sentinel. `ListListView` leaves `empty_date` unset when the yearly rate is 0, so the
  template shows a blank.

## Working style

This is a learning project: the owner is an experienced Python developer learning Django
and learning how to work well with coding agents.

- Prefer simple, idiomatic Django (generic views, ModelForms, the ORM) over clever or
  heavyweight solutions. Don't add dependencies without asking.
- Explain the Django concept behind a change, not just the change.
- When the owner is fixing something themselves, give hints before solutions.
- Ask before editing files. Run `pytest` after changes and report the real result.
