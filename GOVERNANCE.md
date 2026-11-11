# Governance Note: educommAI Career Planning Assistant

**Creator and accountable owner:** T'Darius Reed (Georgia State University, Robinson College of Business), course project.
**Contact:** [add your school email here]. Report a problem or ask for data removal there.
**Audience:** students in grades 6-12, and the parents, guardians, teachers, or counselors helping them. Intended for use with
adult guidance. This is a class project and has not had a legal or privacy review (for example COPPA or FERPA); it is not a
school-approved product.

## 1. What the agent reads
| Input | Source | Notes |
|---|---|---|
| What the user types in chat | The user | Trimmed to 2,000 characters. Emails, phone numbers, SSNs, and street addresses are replaced with placeholders **before** the message is searched, sent to a model, or saved to the profile. |
| Profile fields (role, grade, interests, classes, city/state, things that matter, goal) | The user, via chat or the sidebar form | Asked for in plain words. The screen tells users not to share their full name, address, phone, or school. |
| Public web pages | DuckDuckGo search (`ddgs`) | The **search query** (grade level, interests, city/state, topic) is sent to DuckDuckGo. Result titles and snippets come back. |
| Trusted documents (optional) | `data/knowledge/` | Empty by default. |

## 2. What the agent stores, and where
| Data | Where | How long |
|---|---|---|
| Profile (the fields above, scrubbed) | SQLite file `data/educomm.db` **on the server hosting the app** (on free cloud hosts this disk is wiped when the app restarts) | Until the user deletes it, or the host resets the disk |
| Chat messages | Server memory for that visit only (Streamlit session state, last 40 messages, shown back to the user as typed) | Gone when the session ends or the app restarts. **Never written to disk.** |
| Search results | In-memory cache, 64 queries, 1 hour | Gone when the app restarts |
| "How I got this answer" trace | In memory for the latest answer only | Written to a file **only** if the creator runs the command line with `--trace` |
| Evaluation runs | `evals/results/` | Uses made-up test profiles, never real user data |

- No accounts, names, or logins. Each browser session gets a random id (it is put in the URL only if the host sets `EDUCOMM_URL_ID=1`).
- Users can delete one field (the X next to it) or everything ("Delete everything about me") at any time.
- **Third parties that see data:** DuckDuckGo (search queries); the hosting provider (normal server logs); and, **only if a hosted model is configured**,
  that model provider (the profile, the question, and source snippets). With a local Ollama model or with the model switched off, no model provider sees anything.
- The creator does **not** collect or read user conversations (no logging), so there is no transcript to review or leak. This also means misuse
  can only be found through the evaluation results, not by reading real chats.

## 3. Where human approval and review happen
1. **Before a plan is used (in the app):** every plan or reminder answer is labeled a draft. The calendar (.ics) download is locked until the user
   ticks "A parent, teacher, or counselor has reviewed this plan with me." This is a **confirmation by the user**, not a check by the system:
   the app cannot verify that an adult actually looked. It exists to put a human in the loop before reminders are created.
2. **In every plan answer:** a note says to confirm dates and requirements with the school counselor and the official page.
3. **Dates:** the agent shows a deadline only when a search result states it, with its source number, and flags a guessed year. Otherwise it says it
   found none. A person must confirm any date on the official site.
4. **Self-harm language:** the agent stops career help and points to a trusted adult, 988, and 911. It is a pointer to humans, not a replacement.
5. **Before release (creator):** the creator runs the evaluation harness (`python -m evals.run_evals`), reads the failures in `evals/results/RESULTS.md`,
   and records the analysis in `evals/ANALYSIS.md`. A release with failing safety cases is not shared.

## 4. What users can and cannot make the agent do
**Can:** ask about careers, classes, majors, programs, free learning resources, scholarships; take the interest quiz; get a checklist and a
month-by-month plan; download calendar reminders; view and delete their stored profile.

**Cannot (enforced in code, tested in the evaluation):**
- Change its rules or read its instructions. Prompt-injection phrases are blocked.
- Get unsafe content (explicit or weapon-making requests are refused).
- Get a link that is not from a real search result. The verifier strips any other link.
- Get a deadline that no source states.
- Get personal details repeated back. They are scrubbed from the question and from the answer.
- Make the agent act in the world. It is read-only: it sends no email, submits no forms, signs nobody up, and **cannot push reminders** (it only creates a file).

**Limits users should know:** it can be wrong or out of date. It can miss local programs. Its safety filter is a pattern list, not a perfect
classifier, and it does not scrub names. It is not a substitute for a school counselor.

## 5. Accountability
T'Darius Reed built, deploys, and maintains the system and is responsible for: what it stores, the accuracy of this note, fixing reported
problems, and taking the app down if it cannot be made safe. Search, hosting, and model providers are separate services with their own terms;
the creator chose them and is responsible for disclosing them here.
