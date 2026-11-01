---
name: req-feature
description: >-
  Requirements-first workflow for changing what code does, in projects that track
  requirements with jamb (YAML requirements in git, linked to pytest tests). The user
  describes the behavior they want; you check existing requirements, draft the user need
  (UN) and software requirements (SRS) with concrete examples, stop at two human approval
  gates (the user runs `jamb review mark`), then write failing tests from the approved
  examples, implement until they pass, and validate the trace. Use it whenever the user
  invokes /req-feature, or asks for a new feature or a behavior change in a repo that has
  a jamb `reqs/` tree or `[tool.jamb]` in pyproject.toml, even if they don't mention
  requirements. Not for pure refactors, docs, or tooling changes that don't change
  behavior.
---

# Requirements-first feature workflow

The user says what they want the code to do. Requirements are written and approved
*before* tests, and tests *before* code, so that:

- the user agrees to behavior in words and numbers they understand (not code),
- every behavior change leaves a reviewed record in git, and
- the tests check the approved requirement, not whatever the code happened to do.

The user's approval is the point of the process. You draft; they decide. You can't approve
anything yourself: `jamb review mark` / `review clear` record a *person's* approval, so you
never run them (projects often block them in `.claude/settings.json`), and you never write
or copy a `reviewed:` value or a link hash into a YAML file. Hand-forging either would make
the record claim an approval that didn't happen.

## Before you start: learn this project's setup

Read these once per session; projects differ.

- `CLAUDE.md` (and any requirements notes it points to): hierarchy, area names, writing
  rules, git rules. Project rules win over this skill where they conflict.
- `pyproject.toml` → `[tool.jamb]`: `test_documents` are the SRS-level documents tests
  link to.
- `uv run jamb info`: the document tree (which documents exist and their parents).
  Use the project's own runner (`uv run`, `poetry run`, plain `jamb`) as `CLAUDE.md` says.
- `uv run jamb validate`: the starting state. If it already has warnings unrelated to this
  request, note them so you don't confuse them with your own changes later.

## Stage 1: check what already exists

Most requests change existing behavior rather than add a new need. Before drafting:

1. Search the requirements for the topic: `uv run jamb item list`, and `grep -ril "<keywords>" reqs/`.
2. Find the tests that cover the related items: `grep -rn 'requirement("<UID>"' <test dirs>`.
3. Tell the user what you found and which kind of change this is:
   - **New need**: no existing UN covers it. Go to stage 2.
   - **Change to existing behavior**: name the UN/SRS items and tests affected. You'll edit
     those items rather than adding duplicates; a duplicate would silently contradict the
     old item. Editing a UN makes its SRS children suspect, which is jamb working as
     intended.
   - **Bug fix**: the code doesn't do what an approved SRS item already says. Skip the
     gates: write a failing test for that SRS item (stage 5), then fix (stage 6).
   - **Refactor / no behavior change**: this skill doesn't apply. The check is that
     requirements don't change and all tests still pass.

If the request is ambiguous, ask now, before drafting. A question here is cheaper than a
rejected draft.

## Stage 2: draft the user need (UN)

- In the **user's voice**, one need per item, saying *why*: "I need to know when we'll run
  out so I can order more in time."
- No implementation detail; this is what the user approves, so it must make sense without
  reading code.
- New item: `uv run jamb item add <UN-doc> --links <parent-UID> --header "…" --text "…"`
  (check `jamb info` for the UN document's prefix and parent). Edited item: edit the
  `text:`/`header:` in its YAML file and leave every other field alone.
- Run `uv run jamb validate` to catch YAML mistakes (a bad quote breaks the whole tree).

### Gate 1

Show the user the UN text and its UID, then stop. Tell them exactly what to run in their
own terminal once they're happy, e.g.:

```
uv run jamb review mark UN007
```

They may edit the wording themselves first; that's welcome. Don't continue until they
reply, and when they do, re-read the file (it may have changed) and confirm with
`uv run jamb validate` that the item no longer shows "has not been reviewed". Saying
"looks good" in chat isn't the record; the review mark is.

## Stage 3: draft the SRS items with examples

For each piece of behavior the need requires:

- **Area**: put it in the SRS document for the feature *as the user sees it* (where the user
  sees the result), not by code module. If no existing area fits, propose a new one and ask;
  it needs a folder, `.jamb.yml`, a never-reused prefix, and an entry in `test_documents`.
- **Text**: describe the system ("The dashboard shows…", "The user can…"), present tense.
  Be exact about scope (per item or overall? latest by date or by entry?). State edge
  cases: no data, zero, rounding, invalid input. Don't claim more than will be built.
  Include at least one worked example with numbers in the text itself.
- **Create**: `uv run jamb item add <SRS-doc> --links <UN-UID> --header "…" --text "…"`.
  Never use `--before`/`--after` or `jamb reorder`; UIDs are permanent names.

Then build an **examples table** covering every SRS item, one row per case, including the
edge cases and at least one "what it does *not* do" row:

| SRS | Given | When | Then |
|---|---|---|---|
| DASH005 | 120 bales, using 2.0 bales/day | dashboard loads | shows "8 weeks, 4 days" |
| DASH005 | no withdrawals yet | dashboard loads | shows a blank |
| DASH005 | 0 bales left | dashboard loads | shows "Empty" |

Each row becomes one test in stage 5, so the user is approving the test cases in plain
language. Numbers they can check with a calculator catch vague wording before code exists.

### Gate 2

Show the SRS texts, UIDs and the examples table, then stop. Tell them what to run:

```
uv run jamb review mark DASH005
uv run jamb review clear DASH005
```

(`mark` approves the item's text; `clear` confirms its links to the approved UN.) When they
reply, re-read the files and run `uv run jamb validate -e`; it should pass, or show only
warnings that existed before you started. If your items still show "not been reviewed" or
"no stored hash", say which and wait.

## Stage 4: plan the code change (only if it's large)

For a change touching several files, outline the plan in a few lines before writing code,
so the user can redirect early. Small changes can go straight to stage 5.

## Stage 5: write the tests first, and show them failing

- One test per examples-table row (or a parametrized test with one case per row), marked
  with the SRS UIDs it checks: `@pytest.mark.requirement("DASH005")`. Mark only
  requirements the test actually asserts; tests never get UN markers (they reach the UN
  through the SRS links).
- Follow the project's test layout and helpers; put tests where the project's conventions
  say (often a file named after the SRS area).
- Run just the new tests and show the user they **fail**, and fail for the right reason
  (missing behavior, not a typo or import error). A test that has never failed hasn't
  shown it can catch anything.

## Stage 6: implement

Write the simplest code that makes the new tests pass, following the project's style
rules. Then run the full suite. If an existing test breaks, it's either a real regression
(fix the code) or evidence that this change alters an approved requirement you didn't
identify in stage 1; in that case stop and tell the user rather than editing the old test
or requirement to fit.

If while implementing you find the approved wording is wrong or incomplete, stop and
propose the edit. Never change a requirement just to make a test pass; that reverses the
whole process.

## Stage 7: verify and report

Run:

```
uv run jamb validate -e
uv run pytest --jamb
```

Report, briefly:

- **Requirements**: UIDs added or changed, with one-line summaries.
- **Tests**: new tests, the UIDs each covers, and that you saw them fail before the code
  existed.
- **Code**: files changed and what each change does.
- **Results**: the real `validate` and `pytest --jamb` output (pass counts, coverage). If
  something failed, say so and show it.
- **For the user**: anything still awaiting their review, docs that now look out of date
  (e.g. a known-gaps list in `CLAUDE.md`), and a suggested commit message.

Don't create branches, commit or push unless the user asks or the project says otherwise;
the user decides how changes land.
