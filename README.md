# educommAI - Career Planning Assistant

Personalized assistant for 6th-12th grade students and the parents, guardians, teachers or counselors helping them:
careers that fit, what school or training they need, classes, programs, free learning resources, scholarships,
a checklist and month-by-month plan, and downloadable calendar reminders. Built to run on an 8 GB laptop.

    safety gate -> profile -> keyword router -> specialists search in parallel
                -> ONE optional model call (writes the answer) -> verifier -> reply

The model is optional. With no model (or if it fails mid-answer) the answer is built straight from the
search results. Every link shown to the student comes from a real search result; the model only writes
source numbers like [1], and the verifier turns them into links.

## What it handles
| Who | Ask | You get |
|---|---|---|
| High schooler (e.g. finance) | "Make me a personalized roadmap" | careers, recommended classes and college majors, scholarships, checklist, month-by-month plan |
| Middle schooler, undecided | "I like math and science" / the **Interest quiz** | top career clusters (16 national clusters), student-friendly descriptions, summer programs, free learning resources |
| Busy parent | "My daughter is in 9th grade. How can I help her prepare for college?" | community programs, scholarships, college-prep checklist, month-by-month plan in plain language |

- First message: say who you are (student or parent), grade, interests; city or state is optional and used to find local programs.
- **Deadlines are never invented.** Dates appear only when a search result states them (shown with its source number; if the
  source gives no year, that is flagged). Otherwise the app says it found none and points to the official page.
- **Reminders:** the app cannot send notifications. It gives a `.ics` file (monthly plan + any sourced dates, alert one day before)
  that opens in Google, Apple or Outlook calendars. CLI: `python cli.py -q "..." --ics plan.ics`.
- The quiz, plan, checklist and deadline finder need no model; only the optional write-up does.

## Milestone II: what was added
- **Memory (the extension):** the student's profile is saved in SQLite and changes later answers (grade, interests, location). It is scrubbed
  of personal info, visible in the sidebar, and deletable. Within a session it persists across turns; across visits only if `EDUCOMM_URL_ID=1`.
- **Tools:** web search (DuckDuckGo) and a calendar (.ics) generator.
- **Human review:** plans are drafts; the calendar file is released only after the user confirms an adult reviewed it.
- **Evaluation:** `evals/` (see below). **Governance:** `GOVERNANCE.md`.

## Public deployment (Streamlit Community Cloud, no login for visitors)
1. Push this folder to a GitHub repo. At share.streamlit.io choose the repo, branch, and `app.py`; set visibility to public.
2. Under **Settings > Secrets** add (top-level keys become environment variables): `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` for any
   OpenAI-compatible host. Ollama is not available there. Without these the app still answers (from sources, no model), so test both.
3. Open the URL in a private window, confirm you are not asked to sign in, and run one question before class. Free apps sleep, so wake it first.
4. Storage is wiped when the app restarts; that is expected (stated in `GOVERNANCE.md`).

## Evaluation (`evals/`)
    python -m evals.run_evals            # live: real search + your model. Writes evals/results/RESULTS.md and latest.json
    python -m evals.run_evals --runs 5   # more repeats
    python -m evals.run_evals --offline  # no network; only checks the harness itself
19 cases (12 normal, 7 adversarial) in `evals/cases.jsonl`, each run 3 times with a fresh assistant, reported as pass@1, pass@3, and all-3.
Edit the cases or add checks in `evals/run_evals.py`. Write up the failures in `evals/ANALYSIS.md`.

## Run
    pip install -r requirements.txt
    streamlit run app.py
Optional model (about 2 GB): `ollama pull qwen2.5:3b` (or `qwen2.5:1.5b` on tight machines). Without it the app
still works. Toggle "Use the AI model" in the sidebar, or set `LLM_MODE=off`. Any OpenAI-compatible host works
via `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` (see `.env.example`).

Memory tips for Ollama: `OLLAMA_KEEP_ALIVE=2m` (unload soon after use), `OLLAMA_MAX_LOADED_MODELS=1`,
`OLLAMA_NUM_PARALLEL=1`, `OLLAMA_CONTEXT_LENGTH=4096`. Free the model now with `ollama stop qwxen2.5:3b`.
File watching is off (`.streamlit/config.toml`), so restart the app after editing code.

## Test (no model or internet needed)
    pip install -r requirements-dev.txt && pytest

## Layout
- `core/` assistant (the turn), orchestrator (router), executor (searches), writer, verifier, safety, llm_client, models, tracing, planner, deadlines, ics, quiz
- `agents/` specialists (career explorer, education, courses, programs, resources, funding, next steps, plan) and intake (role, grade, interests, location)
- `tools/` web search (cached) and source ranker; `memory/` profile (SQLite) and optional knowledge store
- `ui/` + `app.py` Streamlit; `cli.py` terminal runner; `data/knowledge/` optional trusted documents

Privacy: no chat history or traces are kept; personal info is scrubbed before storage or search;
students can see and delete everything. The profile lives under a random id in the page URL.
