"""
Session management submodule for HtmlGraph SDK.

Provides session lifecycle operations, handoff context, and continuity.
"""

from __future__ import annotations

from htmlgraph.sdk.session.continuity import SessionContinuityMixin
from htmlgraph.sdk.session.handoff import SessionHandoffMixin
from htmlgraph.sdk.session.info import SessionInfoMixin
from htmlgraph.sdk.session.manager import SessionManagerMixin

__all__ = [
    "SessionManagerMixin",
    "SessionHandoffMixin",
    "SessionContinuityMixin",
    "SessionInfoMixin",
]
