# Requirements tracking in Hay Logger

Notes from setting up requirements tracking in this repo (October 2026): the goals, the
tool, the choices made, and the practices to follow. `CLAUDE.md` has the short version.

## 1. Goals

Requirements tracking here has two jobs:

1. **Keep developers and users in sync.** Users agree to what will be built, in words they
   understand, and developers can see exactly what was agreed.
2. **Be the record when a user says "you didn't do what I asked."** For any feature we
   should be able to show what was asked, that it was agreed and when, whether it changed,
   and that it was built and tested.

Everything below follows from those two goals.

## 2. Choosing a tool

We chose **[jamb](https://jamb.readthedocs.io/)**, a pytest plugin for requirements
traceability, written mainly for medical-device software (IEC 62304). Requirements are YAML
files in git, tests link to them with `@pytest.mark.requirement("SRS001")`, and it produces
traceability matrices (HTML, Markdown, JSON, CSV, Excel). It checks for broken links,
cycles, orphan items and uncovered requirements, and flags children as *suspect* when a
parent changes.

Why it fits: the repo already uses pytest, so tests become the evidence for requirements,
and requirements live in git, so they're reviewed in pull requests next to the code.

Caveats: it's young and niche, and parts of it (regulatory matrices, risk documents) are
more process than a one-person project needs. Its scope stops at traceability: no
project management, document control or electronic signatures.

Alternatives we looked at:

| Tool | Approach | Good for |
|---|---|---|
| **Doorstop** | YAML requirements in git, CLI, links between levels | The established, simple option; jamb's model is similar |
| **StrictDoc** | Its own text format, HTML output, web UI | Writing structured requirement documents (started as a Doorstop fork) |
| **Sphinx-Needs** | Requirements as directives in Sphinx docs | Projects already on Sphinx; powerful but heavier |
| **pytest-bdd** | Gherkin scenarios (Given/When/Then) that run as tests | When the requirement and the test should be the same thing |
| **No tool** | `REQUIREMENTS.md` with IDs plus a custom pytest marker | Learning the idea before picking a tool |

The best practice that matters more than the tool: **requirements as text in version
control, linked to tests, reviewed like code.**

## 3. Document hierarchy patterns

Every pattern breaks requirements into levels, each more specific than the one above, and
each level gets its own kind of check. They differ in how many levels there are and
whether there's a separate risk or safety branch.

**The V-model (regulated industries).** Requirements go down the left side, tests come
back up the right, and each test level checks the matching requirement level:

```
User needs ─────────────────────── Validation (did we build the right thing?)
  System reqs ─────────────── System tests
    Software reqs ─────── Integration tests
      Design / units ── Unit tests
```

| Domain | Standard | Levels |
|---|---|---|
| Medical | IEC 62304, FDA design controls | User needs → system/software requirements, plus hazard → risk control (ISO 14971) |
| Aerospace | DO-178C | System → high-level → low-level requirements → code |
| Automotive | ASPICE, ISO 26262 | Stakeholder → system → software → architecture → units, plus safety goals → safety requirements |
| Cybersecurity | ISO 21434 and others | Threat → security goal → security requirement |

**Systems engineering (INCOSE, ISO/IEC/IEEE 29148).** Stakeholder → system → subsystem →
component requirements. Used when the product splits into parts (hardware, firmware, cloud)
that each need their own requirements.

**Agile backlogs.** Epic → feature → user story → acceptance criteria, usually in Jira.
Stories are disposable: once done, nobody keeps them current. **We ruled this out** for
that reason. A record that stops being updated can't settle a dispute.

**BDD / specification by example.** Feature → scenario. The scenario is both requirement
and test, so it can't drift from the code.

**Flat.** Requirements → tests. Common for small projects and libraries.

**What decides the depth:**
- **Who has to be convinced.** Regulators want the full chain; a solo developer doesn't.
- **Whether the system splits into parts.** Each split tends to add a level.
- **Whether failures can hurt someone.** That's what adds a risk branch.

**The hierarchy you'll actually keep current beats the most thorough one.** Every extra
level is more to re-review on every change, and that's how requirement docs go stale.

## 4. The hierarchy in this repo

`jamb init` creates the full medical layout:

| Folder | Stands for | Contents |
|---|---|---|
| `prj/` | Project | The root item naming the product |
| `un/` | User Needs | What the user wants, in their words |
| `sys/` | System requirements | What the whole system must do |
| `srs/` | Software Requirements Specification | Specific, testable software behaviour |
| `haz/` | Hazards | What could go wrong and cause harm |
| `rc/` | Risk Controls | How a hazard is reduced |

We cut it down to:

```
PRJ ── UN ── SRS  ◄── pytest tests link here
```

- **`sys/` removed:** for a single app it repeats UN in more formal words.
- **`haz/` and `rc/` removed:** risk analysis is worth practising one day ("running out of
  hay in winter" is a real hazard), but not needed now.
- `pyproject.toml` has `test_documents = ["SRS"]` (tests link to SRS) and
  `trace_to_ignore = ["PRJ"]` (every item traces to the root, so tracking it adds nothing).

## 5. Writing good requirements

### User needs (UN)

- **In the user's voice**, as a need: "I need to know when we'll run out so I can order
  more in time."
- **Say why**, so a later reader can judge whether a change still serves the need.
- UN is the only level users are asked to approve, so it must make sense without
  technical knowledge.

### Software requirements (SRS)

- **Describe the system, not a person:** "The dashboard shows…", "The user can…". Not
  "I can…". Use the present tense ("shows", not "will show") so the set reads as one
  description of the system.
- **Include a worked example with numbers.** Vague wording is what disputes are made of; a
  user can check an example with a calculator. Use the same numbers as the tests where
  possible (SRS006 and `test_dashboard_burn_rates_and_empty_date` both use 635 bales at
  1 bale a day).
- **State the edge cases.** What happens with no data, with zero, with rounding?
- **Be exact about scope.** Per hay type or overall? Latest log or latest withdrawal?
- **Don't claim more than the code does.** If it's approximate, say so.
- **Describe what the code does now**, not what it ideally should do. If they differ,
  that's a bug or a change request, and it should be written down as one.

### Lessons from reviewing SRS010 (the throw-down number)

The first draft had these problems, all typical:

| Problem | Why it matters | Fix |
|---|---|---|
| Unclosed quote in `text:` | One bad YAML file makes `jamb validate` fail for the whole tree | Check quoting on multi-line text; run `jamb validate` after editing |
| "bails" | These are the words users approve (the code already renamed `BailCount` for this) | "bales" |
| "last log" | The code uses the latest *withdrawal* of *that hay type*: a delivery doesn't reset it | Say exactly what's counted |
| "I can withdraw" | SRS describes the system | "the user can withdraw" |
| "without changing the empty date" | Logging the withdrawal shifts the 365-day rate slightly, so the date moves a little | "keeps roughly the same empty date", or describe it as bales expected to have been used since the last withdrawal |
| Rounding and blank case not stated | These are exactly what someone argues about later | Rounded to whole bales; blank with no withdrawals |

## 6. The workflow

1. **A request comes in.** Write or edit a UN item in a pull request. Record who asked and
   why in the commit message or PR description (jamb has no field for this).
2. **The user approves it.** Ideally they approve the PR themselves. If not, record their
   approval (e.g. an email) in the PR, then `jamb review mark UN00x` and commit.
3. **Developers write the SRS items** linked to that UN (`jamb item add SRS --links UN00x`),
   review them, and write tests marked `@pytest.mark.requirement("SRS00x")`.
4. **CI enforces it:** `jamb validate` fails on broken or suspect links; `pytest --jamb`
   reports coverage and pass/fail.
5. **Release:** keep the matrix with the release (attached to a git tag or as a CI
   artifact), so for any version you can show what was required and what passed.

Where each answer comes from in a dispute:

| Question | Evidence |
|---|---|
| What did they ask for? | The UN item text |
| Did they agree, and when? | The `reviewed:` hash shows *that* it was approved; the git commit shows *who* and *when* (jamb doesn't record the reviewer) |
| Did they change their mind? | Git history of the UN file; edits also make linked SRS items suspect |
| Did we build and test it? | The matrix from `pytest --jamb`: requirement → tests → pass/fail |

Limit: this is evidence, not a contract. If a user never approves anything, the record
only shows what we believed they wanted. The approval step is what gives it weight.

## 7. Reviews: `mark` vs `clear`

| | `jamb review mark` | `jamb review clear` |
|---|---|---|
| Question | Is this item's own text right? | Is this child still right given its parent? |
| Stores | A hash of the item's content in `reviewed:` | A hash of each parent, on the link (`- UN006: kkKF…`) |
| Undone by | Editing the item | Editing the parent |
| Warning | "has not been reviewed" | "has suspect links" / "no stored hash" |

The hash covers `text`, `header`, `links` and `type`, not other fields.

Example: the user changes UN003 to "know when I'll run out, **with 2 weeks' warning**".
UN003 loses its review; the user re-approves it with `mark`. SRS005 and SRS006 haven't
changed, so they still look reviewed, but their links to UN003 are now **suspect**. A
developer must decide whether they still meet the need (here they don't: nothing warns in
advance), fix or add SRS items, and only then `clear` the links. Without `clear`, a parent
could change while every child still looked approved.

Who runs what:
- `mark` on UN: the **user** ("that's what I need")
- `mark` on SRS: a **developer** ("this requirement is well written")
- `clear`: a **developer** ("this SRS still meets its changed UN")

## 8. Linking tests to requirements

- **Markers go on SRS only.** UN is checked by the user accepting the system (validation),
  not by automated tests (verification). Tests reach UN through the SRS links, and the
  matrix shows the whole chain. Marking tests with UN IDs too would create a second,
  driftable source for the same link.
- **Only mark a requirement the test actually asserts.** A test that checks a page loads
  doesn't verify "the empty date is blank when the rate is 0". Marking it would overstate
  coverage, which is worse than an honest gap.
- One test can cover several requirements (`@pytest.mark.requirement("SRS004", "SRS005")`),
  and one requirement can have several tests.
- Tests with no matching requirement (version footer, migration test) stay unmarked.

Coverage as of 2026-10-26: 9 of 10 SRS items covered, all passing. Known gaps:
- **SRS003 (horse-count pre-fill) has no test.**
- **The "blank" cases in SRS005/006** are only smoke-tested (the `test_index_loads_*`
  tests in `test_bugs.py`). One assertion each on the dashboard row would let them be
  marked properly.

## 9. Organising many requirements

Three tools, usually combined on large projects:

1. **Separate documents per functional area.** jamb finds any folder with a `.jamb.yml`,
   so `reqs/srs/dash/` (prefix `DASH`), `reqs/srs/log/` (`LOG`), each with `parents: [UN]`,
   listed in `test_documents`. Each area gets its own numbering and can be reviewed and
   published on its own. This is how large Doorstop, aerospace and automotive projects
   are split. Downside: an item lives in exactly one folder.
2. **Custom attributes for cross-cutting views.** Any extra YAML key (`area: dashboard`,
   `visible_to_user: true`, `release: 0.4`) is kept. It isn't part of the review hash, so
   re-tagging doesn't cancel an approval. Show it in the matrix with
   `[[tool.jamb.matrix_columns]]` (`key`, `header`) in `pyproject.toml`; list items by tag
   with `grep`. "What the user sees" is cross-cutting (the empty date is both a calculation
   and something visible), so it's a tag, not a folder.
3. **Heading and info items** (`type: heading` with a `level`, `type: info`) for section
   titles and notes in published documents. They need no tests. But items are ordered by
   UID, so inserting a heading means `--before`, which renumbers everything after it.

**UIDs are permanent names, not positions.** jamb updates test markers when it renumbers,
but not the UIDs quoted in emails, PRs or approvals. Never renumber to fill gaps or to make
room. Use folders for structure and tags for views instead.

Rule of thumb: one folder until it's hard to scan (roughly 30–50 items), then split by area.

## 10. jamb quick reference

```bash
uv run jamb item add SRS --links UN003 --header "Title" --text "..."  # new item
uv run jamb item list SRS                     # list items
uv run jamb validate                          # links, suspect links, reviews, YAML
uv run jamb review mark UN003                 # approve an item's text (or: SRS, all)
uv run jamb review clear SRS005               # confirm a child still fits its parents
uv run pytest --jamb                          # run tests + coverage summary (writes .jamb)
uv run jamb matrix matrix.html               # matrix from saved coverage data (.html/.md/.csv/.xlsx/.json)
uv run jamb publish SRS srs.html              # document; extension picks the format (no path: Markdown to stdout)
```

Quirks found so far:
- `jamb check` (static, no test run) misses markers on methods inside a Django `TestCase`
  class and reports SRS008 as uncovered. `pytest --jamb` counts them correctly; use it in CI.
- `jamb item add` without review leaves links with "no stored hash" warnings until
  `review clear` is run. Expected, not an error.
- `.jamb`, `matrix.html`, `srs.html` and `all.html` are generated output.

## 11. Next steps

- Write a test for SRS003; add the blank-case assertions for SRS005/006.
- Review and approve the current items (`review mark all`, `review clear all`, commit).
- Add `jamb validate` and `pytest --jamb` to the GitHub Actions workflow.
- Save the matrix with each release.
- Decide whether generated jamb output goes in `.gitignore`.
- Optionally: an `area:` attribute and matrix column, to practise grouping.

## Sources

- [jamb on PyPI](https://pypi.org/project/jamb/) and [documentation](https://jamb.readthedocs.io/)
- [jamb concepts](https://jamb.readthedocs.io/en/latest/user-guide/concepts.html)
- [StrictDoc FAQ (relation to Doorstop and Sphinx)](https://strictdoc.readthedocs.io/en/latest/strictdoc_02_faq.html)
- [Sphinx-Graph (compares Sphinx-Needs and Doorstop)](https://sphinx-graph.readthedocs.io/en/main/)
- [RTEMS requirements tooling notes](https://git.rtems.org/rtems-docs/tree/eng/req/tooling.rst)
