"""Terminal runner (no Streamlit).
  python cli.py -q "What careers fit me?" --profile sample_profiles/finance_11th.json
  LLM_MODE=off python cli.py -q "..."      # no model at all
"""

import argparse
import json
import sys

from core.assistant import Assistant
from memory.session_memory import SessionMemory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--question")
    parser.add_argument("--profile", help="JSON profile to load first")
    parser.add_argument("--user", default="cli-user")
    parser.add_argument("--ics", help="write the reminders calendar (.ics) to this file when an answer has one")
    parser.add_argument("--trace", help="write the trace to this .json file")
    args = parser.parse_args()

    assistant, session = Assistant(), SessionMemory()
    if args.profile:
        with open(args.profile, encoding="utf-8") as f:
            assistant.update_profile(args.user, json.load(f))

    def ask(text):
        turn = assistant.handle(args.user, text, session)
        print(f"\n{turn.answer}\n")
        if turn.ics and args.ics:
            with open(args.ics, "w", encoding="utf-8", newline="") as f:
                f.write(turn.ics)
            print(f"[calendar saved to {args.ics}]")
        if turn.issues:
            print(f"[checks: {'; '.join(turn.issues)}]")
        if args.trace:
            with open(args.trace, "w", encoding="utf-8") as f:
                f.write(turn.trace.to_json())

    if args.question:
        ask(args.question)
        return 0
    print(f"\n{assistant.greet(args.user, session).answer}\n")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        if text:
            ask(text)


if __name__ == "__main__":
    sys.exit(main())
