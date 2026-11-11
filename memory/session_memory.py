"""Per-browser-session conversation state (no chat history is kept: nothing reads it)."""

from __future__ import annotations


class SessionMemory:
    def __init__(self):
        self.greeted = False
        self.awaiting: str | None = None          # profile field the intake just asked about
        self.pending_question: str | None = None  # question to answer once intake finishes
        self.intake_active = False                # a new user is being set up this session
        self.location_asked = False               # the optional location question was asked (or skipped)

    def clear(self) -> None:
        self.__init__()
