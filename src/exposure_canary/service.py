"""Facade used by the CLI and the MCP server."""

from __future__ import annotations

from datetime import datetime

from .errors import InputError
from .events import import_webhook
from .models import Canary
from .report import render_report
from .state import State
from .tokens import build_canary

__all__ = [
    "State",
    "create_canary",
    "import_webhook",
    "render_report",
]


def create_canary(
    state: State,
    *,
    kind: str,
    label: str,
    asset: str,
    owned: bool,
    collector: str | None = None,
    zone: str | None = None,
    domain: str | None = None,
    now: datetime | None = None,
) -> Canary:
    """Create a canary on an owned asset and persist it."""
    for _ in range(5):
        canary = build_canary(
            kind=kind,
            label=label,
            asset=asset,
            owned=owned,
            collector=collector,
            zone=zone,
            domain=domain,
            now=now,
        )
        if canary.id not in state.canary_map():
            state.canaries.append(canary)
            state.save()
            return canary
    raise InputError("Não foi possível gerar um id exclusivo.")
