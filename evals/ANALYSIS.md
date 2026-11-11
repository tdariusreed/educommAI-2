# Failure analysis and observed weaknesses

> Fill in the **Observed in the live run** column from `evals/results/RESULTS.md` after you run
> `python -m evals.run_evals` on a machine with internet. The rest is what the design already tells us.

## How to read the results
- **pass@1** is the average single-run pass rate; **pass@3** is the chance at least one of 3 runs passes; **all-3** is the share of
  cases that passed every run (consistency). A big gap between pass@1 and all-3 means flaky behavior, usually search or model.
- Deterministic parts (safety, routing, plan, calendar, quiz) should score 100% every run. Variation comes from web search
  results and, when a model is on, from the write-up.

## Known weaknesses (design-level) and how the harness covers them
| Weakness | Cause | Covered by case | Observed in the live run |
|---|---|---|---|
| Programs can miss the student's interests (e.g. history and art) | Search engines return generic "summer camp" lists | n12 (`queries_include`), n06 | _fill in_ |
| Fewer than 1 usable source on some questions | DuckDuckGo rate limits or empty results; hosted IPs are throttled more | every `min_sources` check | _fill in_ |
| Router can pick the wrong specialists | It is keyword matching, so unusual wording or a stray word like "interest" misroutes | n01-n09 (`agents_include`) | _fill in_ |
| Model may state a date or fact the source doesn't contain | Small models drift; the verifier removes bad links and numbers, not wrong claims | n04, n05, n09, a06 (`no_invented_dates`) | _fill in_ |
| Safety is pattern matching | A new phrasing of self-harm or injection can slip through | a01, a02, a07 | _fill in_ |
| Names are not scrubbed from stored or logged text | PII scrubber covers emails, phones, SSNs, street addresses only | a03 checks phones only | _fill in_ |
| Quality depends on the web | Top results can be commercial or outdated | `only_cited_urls` proves links are real, not that they are good | _fill in_ |

## Failures from the live run
_Paste each FAILED or FLAKY case from RESULTS.md with: what failed, the likely cause, and the fix you made or chose not to make._

## What I changed because of the evaluation
_One line per fix, with the before and after score for that case._
