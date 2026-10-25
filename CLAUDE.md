# Hay Logger

Django 5 app for tracking hay bales in a barn: deliveries (DEPOSIT), usage (WITHDRAW),
burn rates and a usage chart. One app, `log_app`. SQLite database at `db/db.sqlite3`.

## Commands

```bash
poetry install                 # dependencies (dev group includes pytest, pytest-django, ruff)
python manage.py runserver     # local dev server
pytest                         # all tests (pytest-django; config in pyproject.toml)
python manage.py makemigrations --check --dry-run   # models match migrations?
ruff check --fix . && ruff format .                 # also run by pre-commit
```

## Deployment

Push to `main` -> GitHub Actions builds the image -> Docker Hub `3ltreilly/hay-logger`
-> the Synology server (`milhouse.local`) pulls it and runs it with `db/` mounted as a volume.
See `wip.sh` for the server commands. The container runs `runserver`; it does not run `migrate`.

## Gotchas

- **Migrations:** the production database has `log_app` migrations 0001–0008 applied
  (verified to match the local files). Never delete, rename or regenerate them. When a
  model changes, run `makemigrations` and commit the new file with the model change.
  0009 (table rename) and 0010 (`Log.date` default) are committed but not yet applied on
  the server: run `migrate` there before deploying them, since the container won't.
- **Time zones:** `USE_TZ = True`. Use `django.utils.timezone.now()`, never
  `datetime.now()`. `log_app/tests.py` still builds naive dates (the RuntimeWarnings).
- **Stored totals:** `BaleCount.total` is a running total updated by hand in the
  `form_valid` methods of `LogCreate`, `LogEdit` and `LogDelete`. Any change to how logs
  are saved must keep it in sync. The usage chart applies an offset because historic totals
  don't match the sum of the logs.
- **Naming:** `BaleCount` is really a hay type (first/second cutting). It was renamed
  from the misspelled `BailCount` in migration 0009, so the old spelling remains only in
  migrations 0003–0008. Don't edit those files.
- **`log_app/test_bugs.py`:** the BUG tests have all been fixed and now act as regression
  tests; every test in the file must stay green.
- **Burn rates:** `burn_rate()` returns the real rate (0 when a hay type has no usage), not
  a sentinel. `ListListView` leaves `empty_date` unset when the yearly rate is 0, so the
  template shows a blank. Known open bug, not covered by tests: the `except
  Log.DoesNotExist: return context` in `ListListView` stops the loop at the first hay type
  with no withdrawals. The owner is fixing it; don't fix it unless asked.

## Working style

This is a learning project: the owner is an experienced Python developer learning Django
and learning how to work well with coding agents.

- Prefer simple, idiomatic Django (generic views, ModelForms, the ORM) over clever or
  heavyweight solutions. Don't add dependencies without asking.
- Explain the Django concept behind a change, not just the change.
- When the owner is fixing something themselves, give hints before solutions.
- Ask before editing files. Run `pytest` after changes and report the real result.
