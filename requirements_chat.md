# Requirements tracking in Hay Logger

Notes from setting up requirements tracking in this repo (October 2026): the goals, the
tool, the choices made, and the practices to follow. `CLAUDE.md` has the short version.

## Rules at a glance

The sections below explain the reasons. These are the rules to follow day to day.

### Writing

- User needs (UN) are in the user's voice, one need each, and say why.
- SRS items describe the system ("the dashboard shows…"), in the present tense.
- Every SRS item has a worked example with numbers, and states its edge cases (no data,
  zero, rounding).
- Describe what the code does now. If that's not what it should do, write a bug or change
  request; don't write the wish as a requirement.
- Don't claim more than the code does.

### Changing behavior

- A behavior change updates its SRS item in the same commit or PR; list the changed UIDs.
- Never edit a requirement just to make a test pass. Flag the mismatch.
- Behavior nobody asked for still gets an SRS item (`derived: true`).
- Retire a requirement with `active: false`; don't delete it. It's part of the record.
- Add items with `jamb item add`; run `jamb validate` after editing any YAML by hand.

### Approving

- Only people approve: users `review mark` user needs; developers `review mark` SRS items
  and `review clear` links. Agents never do (enforced in `.claude/settings.json`).
- Never write a `reviewed:` value or link hash by hand.
- A suspect link means "re-check this child against its changed parent" before clearing.

### Testing

- Test markers go on SRS items only, never on user needs.
- Only mark a requirement the test actually asserts.
- Every SRS item needs a test. A test with no requirement is either undocumented behavior
  or a deliberate smoke test.

### Organizing

- UIDs are permanent names. Never renumber; gaps are fine; never reuse a prefix.
- One folder until it's hard to scan (roughly 30–50 items), then split.
- Split SRS by **feature as the user sees it**, not by code module.
- Split user needs by **who** (user role), not by feature.
- Every SRS document lists every user-need document as a parent.
- Name test files after SRS areas (`test_dash.py` ↔ `DASH`).
- A folder says where a requirement lives (one place). A tag answers a question that cuts
  across folders (user-visible? which release?).
- Read requirements through views (`jamb publish`, `jamb item list`, the matrix), not by
  browsing YAML files.

## 1. Goals

Requirements tracking here has three jobs:

1. **Keep developers and users in sync.** Users agree to what will be built, in words they
   understand, and developers can see exactly what was agreed.
2. **Be the record when a user says "you didn't do what I asked."** For any feature we
   should be able to show what was asked, that it was agreed and when, whether it changed,
   and that it was built and tested.
3. **Keep developers informed about what their code does.** When AI agents write much of
   the code, it's easy to lose track of how the system behaves. The requirements should be
   a current, readable description of the behavior, so a developer can learn what the
   code does without reading all of it, and notice when that changes.

Goals 1 and 2 face the user; goal 3 faces the developers, including the agents, which both
read the requirements and change the code they describe. Everything below follows from
these goals; section 9 covers what goal 3 adds.

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
| `srs/` | Software Requirements Specification | Specific, testable software behavior |
| `haz/` | Hazards | What could go wrong and cause harm |
| `rc/` | Risk Controls | How a hazard is reduced |

We cut it down to:

```text
PRJ ── UN ─┬─ LOG   (SRS: adding, editing, deleting logs)  ◄─┐
           ├─ DASH  (SRS: dashboard numbers)                ◄─┼─ pytest tests link here
           └─ HIST  (SRS: usage chart, CSV export)          ◄─┘
```

- **`sys/` removed:** for a single app it repeats UN in more formal words.
- **`haz/` and `rc/` removed:** risk analysis is worth practicing one day ("running out of
  hay in winter" is a real hazard), but not needed now.
- The SRS level is split by feature area (section 10) into `LOG`, `DASH` and `HIST`.
- `pyproject.toml` has `test_documents = ["LOG", "DASH", "HIST"]` (tests link to the SRS
  documents) and `trace_to_ignore = ["PRJ"]` (every item traces to the root, so tracking it
  adds nothing).

The SRS items started in one `SRS` folder and were split on 2026-10-27. Earlier sections of
these notes use the old IDs where they describe what happened at the time:

| Old | New | Header |
|---|---|---|
| SRS001 | LOG001 | Add a log |
| SRS002 | LOG002 | Edit or delete a log |
| SRS003 | LOG003 | Pre-fill horse count |
| SRS004 | DASH001 | Current total per hay type |
| SRS005 | DASH002 | Burn rates |
| SRS006 | DASH003 | Empty date |
| SRS010 | DASH004 | Withdraw estimate (throw-down) |
| SRS007 | HIST001 | Running total chart |
| SRS008 | HIST002 | Chart date range |
| SRS009 | HIST003 | CSV download |

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
  possible (DASH003 and `test_dashboard_burn_rates_and_empty_date` both use 635 bales at
  1 bale a day).
- **State the edge cases.** What happens with no data, with zero, with rounding?
- **Be exact about scope.** Per hay type or overall? Latest log or latest withdrawal?
- **Don't claim more than the code does.** If it's approximate, say so.
- **Describe what the code does now**, not what it ideally should do. If they differ,
  that's a bug or a change request, and it should be written down as one.

### Lessons from reviewing SRS010, now DASH004 (the throw-down number)

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
4. **CI enforces it:** `jamb validate -e` fails on broken or suspect links and on
   unreviewed items (`-e` turns warnings into errors); `pytest --jamb --jamb-fail-uncovered`
   reports pass/fail and fails if any requirement has no test.
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
UN003 loses its review; the user re-approves it with `mark`. DASH002 and DASH003 haven't
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
- One test can cover several requirements (`@pytest.mark.requirement("DASH001", "DASH002")`),
  and one requirement can have several tests.
- Tests with no matching requirement (version footer, migration test) stay unmarked.

Coverage as of 2026-10-26: 9 of 10 SRS items covered, all passing. Known gaps:
- **LOG003 (horse-count pre-fill) has no test.**
- **The "blank" cases in DASH002/003** are only smoke-tested (the `test_index_loads_*`
  tests in `test_bugs.py`). One assertion each on the dashboard row would let them be
  marked properly.

## 9. Keeping developers informed (working with AI agents)

Goals 1 and 2 are about the *agreement* with the user. Goal 3 is about the *description*
of the code: the SRS should be the place a developer reads to learn what the system does,
and the place a behavior change shows up first. With agents writing code quickly, the
risk isn't missing documentation but documentation that silently stops matching the code.

### What it changes

- **SRS changes travel with code changes.** Any change to behavior, by a person or an
  agent, edits or adds the SRS item in the same commit or PR, and says which UIDs changed.
  A code change with no requirement change is a claim that behavior didn't change, and
  that's worth checking.
- **Review the requirement diff before the code diff.** Ten lines of changed SRS text are
  quicker to read than 200 lines of agent-written code, and they're the part that says
  what the system now does. Then check the code and tests do that.
- **A requirement edit is never a quiet fix.** An agent asked to make tests pass could
  "fix" the requirement to match the code. jamb makes that visible: editing an SRS item
  clears its review, and `jamb validate -e` in CI fails until a person runs
  `jamb review mark`. Human review stops being optional; it's the gate. This is also why
  agents don't run `review mark` or `review clear` themselves.
- **Write down behavior nobody asked for.** Goals 1–2 only need requirements that trace
  to a user need. Goal 3 needs *everything the code does* to be findable. The throw-down
  number was the warning sign: it was on the dashboard and nobody had written down what it
  meant. Behavior without a user need goes in an SRS item with `derived: true` (no parent
  link required). Candidates now: the app version in the footer (a test exists, no
  requirement).
- **Look at coverage in both directions.** `--jamb-fail-uncovered` catches requirements
  with no test. The reverse, tests with no requirement, is behavior that isn't described.
  Each unmarked test should either get a requirement (often a derived one) or be a plain
  smoke or migration test on purpose.
- **Publish it to read it.** `jamb publish SRS srs.html` gives a readable description of
  current behavior; regenerate it rather than keeping a hand-written copy.

### What it reinforces

- **"Describe what the code does now"** (section 5) becomes the core rule, not just a tip.
- **"Only mark what a test asserts"** (section 8) matters more: developers trust the matrix
  to say what's verified.
- **Ruling out agile stories** (section 3): a story describes a change, not the current
  system, so it can't answer "what does the code do?"
- **pytest-bdd** (section 2) looks better for this goal: when the requirement *is* the
  test, it can't drift. Worth an experiment for one feature.

### What it doesn't change

- **The hierarchy.** UN → SRS still fits. Goal 3 is about behavior, which is the SRS
  level, so no new level is needed.
- **Where the "how" lives.** Requirements say *what* the system does. *How* it does it
  (`current_total()` sums the logs; the chart builds running totals before trimming) stays
  in docstrings, comments and `CLAUDE.md`. A design level below SRS is the V-model's next
  step, but it drifts fastest of all, so we'd add one only when we need it.

## 10. Organizing many requirements

Picture a future Hay Logger with several barns, logins, feed costs and "running low"
alerts: about 400 SRS items.

### The problem

```text
reqs/srs/
  SRS001.yml
  ...
  SRS400.yml        ← 400 files; the names tell you nothing
```

`jamb item list SRS` prints 400 lines in creation order, and the chart requirements are
SRS007, SRS008, SRS151, SRS290… scattered through it.

### Split SRS by feature area

jamb treats any folder with a `.jamb.yml` as a document, so each feature area gets its own
folder, prefix and numbering:

```text
reqs/
  prj/
  un/
  srs/
    log/    .jamb.yml  LOG     LOG001–LOG038    adding, editing, deleting logs
    dash/   .jamb.yml  DASH    DASH001–DASH052  totals, burn rates, empty date, throw-down
    chart/  .jamb.yml  CHART   CHART001–CHART030
    export/ .jamb.yml  EXP     EXP001–EXP015    CSV, backups
    barns/  .jamb.yml  BARN    BARN001–BARN041  several barns, moving hay between them
    users/  .jamb.yml  USER    USER001–USER060  login, roles, who logged what
    alerts/ .jamb.yml  ALERT   ALERT001–ALERT035
    costs/  .jamb.yml  COST    COST001–COST045
```

```yaml
# reqs/srs/dash/.jamb.yml
settings:
  prefix: DASH
  digits: 3
  sep: ''
  parents: [UN]
```

```toml
# pyproject.toml
test_documents = ["LOG", "DASH", "CHART", "EXP", "BARN", "USER", "ALERT", "COST"]
```

Now `DASH014` says where it lives, and the dashboard folder holds 52 files, not 400. This
is how large Doorstop, aerospace and automotive projects are split.

### Choosing areas

**Choose areas by feature as the user sees it, not by code module.** Code gets refactored
and modules move; "the dashboard" stays the dashboard, and requirement IDs must stay
stable. Questions to check an area:

- **Would a user name it?** "Dashboard", "chart", "export": yes. "Views", "utils",
  "models": no.
- **Will it survive a refactor?** If moving code between files would make the area wrong,
  it's a code module, not a feature.
- **Can you say in one sentence what belongs in it** (and so what doesn't)?
- **Does it hold roughly 5–50 items?** Fewer: merge it into a neighbor. More: split it.
- **Prefix:** 2–5 capital letters, unique, and never reused, even after an area is retired.

**When a requirement could fit two areas, put it where the user sees the result.** The
empty date is a calculation, but the user sees it on the dashboard, so it's `DASH`. Use a
tag if you also need to find it from another angle.

### Three trees that match

This is what makes a large set workable. Requirement areas, test files and code use the
same names:

```text
reqs/srs/dash/DASH014.yml    "Empty date…"
log_app/tests/test_dash.py   @pytest.mark.requirement("DASH014")
log_app/views/dashboard.py   the code that computes it
```

Working on the dashboard? Everything about it is in three predictable places. The
requirement folders and the test files matter most; code layout can drift, since it
follows the code, not the user.

### Split user needs by role

User needs grow too, though usually far fewer: often 1 user need per 5–10 SRS items, since a
need is broad and the SRS level adds detail. 400 SRS items might mean 40–80 user needs.

User needs are in the user's voice and approved by users, so group them by **who**, not by
feature:

```text
reqs/un/
  owner/  .jamb.yml  OWN    OWN001–OWN030    plan ahead, order hay, costs
  crew/   .jamb.yml  CREW   CREW001–CREW020  daily logging at the barn, from a phone
  books/  .jamb.yml  BOOK   BOOK001–BOOK010  exports, records for taxes
```

- **It's clear who approves what:** `jamb review mark OWN` is the owner approving their
  own needs.
- **Each role's folder reads on its own:** "everything the crew needs" can be sent to the
  crew.
- If roles don't fit a project, group by **activity** (record, plan, review, administer).
  Avoid grouping by software feature: a need isn't tied to one feature.

The user-need folders *won't* line up with the SRS folders, because one feature serves
several roles:

```text
OWN001  "know when we'll run out"       ──►  DASH006 Empty date
CREW001 "know how much to throw down"   ──►  DASH010 Throw-down
CREW002 "log hay from my phone"         ──►  LOG001 Add a log
BOOK001 "records for my accountant"     ──►  EXP001 CSV download
```

That's fine: links (and the matrix) connect the two trees.

**Every SRS document must list every user-need document as a parent.** Tested in a
throwaway project: with `DASH` listing only `OWN`, a `DASH` item linked to `CREW001` gave
*"links to CREW001 in document CREW, which is not a parent document"*, a warning that
`jamb validate -e` turns into a CI failure. Adding `CREW` to the list fixed it:

```yaml
# reqs/srs/dash/.jamb.yml
settings:
  prefix: DASH
  parents: [OWN, CREW, BOOK]
```

Adding a role means adding one line to each SRS document's parents.

### Tags for questions that cut across areas

Folders answer "where does this live?". Tags answer "what does the user see?" or "what's
in 0.5?". Any extra YAML key is kept as a custom attribute:

```yaml
# reqs/srs/dash/DASH014.yml
header: Empty date
text: For each hay type, the dashboard shows an estimated empty date…
links:
- UN003: kkKF…
visible_to_user: true      # custom attributes: not part of the review hash,
release: "0.4"             # so re-tagging doesn't cancel an approval
reviewed: hhZz…
```

```bash
grep -rl "visible_to_user: true" reqs/srs   # every user-visible requirement, all areas
grep -rl 'release: "0.5"' reqs/srs          # what's planned for the next release
```

Add `[[tool.jamb.matrix_columns]]` entries (`key`, `header`) in `pyproject.toml` to show a
tag as a matrix column you can sort and filter.

### Read through views, not files

Treat the YAML files like database rows: storage, not reading material. Day to day:

| I want to… | Use |
|---|---|
| Read everything about the dashboard | `uv run jamb publish DASH dash.html` (one page, with headers) |
| Find a requirement by topic | `uv run jamb item list DASH`, or `grep -ril "empty date" reqs/` |
| See what's tested, and by what | The matrix from `pytest --jamb` |
| See what a change affected | The requirement diff in the PR |
| Open one requirement | By ID: `reqs/srs/dash/DASH014.yml` |

The folders keep each of these views small.

### Headings

jamb also has `type: heading` items (with a `level`) and `type: info` items, for section
titles and notes in published documents; they need no tests. But items are ordered by UID,
so inserting a heading means `item add --before`, which renumbers everything after it.
Use folders for structure instead; add headings only when starting a new document.

### When to split

**UIDs are permanent names, not positions.** jamb updates test markers when it renumbers,
but not the UIDs quoted in emails, PRs or approvals.

Splitting a folder changes UIDs, and what that costs depends on the level:

- **Splitting SRS** (`SRS006` becomes `DASH003`): every test marker for a moved item
  changes, and so does every place the old ID is quoted. Approvals survive: the review hash
  covers text, header, links and type, not the UID, and a moved SRS item still links to the
  same user needs.
- **Splitting user needs** (`UN003` becomes `OWN001`): no test changes, but every SRS item
  linking to a moved need gets a new link, so its review hash no longer matches. Every
  linked SRS item needs `review mark` and `review clear` again, as well as the moved needs.

Both costs grow with the number of items, so the cheapest time to split is early. For SRS
here that's now (10 items), which is why it was split on 2026-10-27; approvals survived, as expected
(`jamb validate -e` passed straight after the move).

## 11. jamb quick reference

```bash
uv run jamb item add SRS --links UN003 --header "Title" --text "..."  # new item
uv run jamb item list SRS                     # list items
uv run jamb validate                          # links, suspect links, reviews, YAML
uv run jamb validate -e                       # same, but warnings fail (for CI)
uv run jamb review mark UN003                 # approve an item's text (or: SRS, all)
uv run jamb review clear DASH002              # confirm a child still fits its parents
uv run pytest --jamb                          # run tests + coverage summary (writes .jamb)
uv run pytest --jamb --jamb-fail-uncovered    # same, but fail if a requirement has no test
uv run jamb matrix matrix.html               # matrix from saved coverage data (.html/.md/.csv/.xlsx/.json)
uv run jamb publish SRS srs.html              # document; extension picks the format (no path: Markdown to stdout)
```

Quirks found so far:
- `jamb check` (static, no test run) misses markers on methods inside a Django `TestCase`
  class and reports HIST002 as uncovered. `pytest --jamb` counts them correctly; use it in CI.
- `jamb item add` without review leaves links with "no stored hash" warnings until
  `review clear` is run. Expected, not an error.
- `.jamb`, `matrix.html`, `srs.html` and `all.html` are generated output.

## 12. Next steps

Done: current items reviewed and approved; generated jamb output kept out of git; SRS split
into `LOG`, `DASH` and `HIST`; the
"behavior changes update requirements in the same change" rule added to `CLAUDE.md`.

- Write a test for LOG003; add the blank-case assertions for DASH002/003.
- Add `jamb validate -e` and `pytest --jamb --jamb-fail-uncovered` to the GitHub Actions
  workflow (after LOG003 has a test, or the build fails).
- Save the matrix with each release.
- Write a derived SRS item for the version footer; decide on the other unmarked tests.
- Optionally: an `area:` attribute and matrix column, to practice grouping; try
  pytest-bdd on one feature.

## Sources

- [jamb on PyPI](https://pypi.org/project/jamb/) and [documentation](https://jamb.readthedocs.io/)
- [jamb concepts](https://jamb.readthedocs.io/en/latest/user-guide/concepts.html)
- [StrictDoc FAQ (relation to Doorstop and Sphinx)](https://strictdoc.readthedocs.io/en/latest/strictdoc_02_faq.html)
- [Sphinx-Graph (compares Sphinx-Needs and Doorstop)](https://sphinx-graph.readthedocs.io/en/main/)
- [RTEMS requirements tooling notes](https://git.rtems.org/rtems-docs/tree/eng/req/tooling.rst)
