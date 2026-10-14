"""Normalize webhook payloads, deduplicate, and assign severity."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import InputError
from .models import Canary, Event, ImportResult
from .state import State
from .tokens import normalize_token

MAX_EVENTS = 1000
MAX_WEBHOOK_BYTES = 2_000_000
DEDUP_WINDOW_SECONDS = 300
_ID_KEYS = ("canary_id", "token", "token_id")
_HINT_KEYS = ("path", "url", "value", "email", "address", "host", "qname", "name")
_TIME_KEYS = ("observed_at", "timestamp", "time", "ts")
_SOURCE_KEYS = ("source", "remote", "ip", "remote_addr", "client_ip")


@dataclass(frozen=True)
class Incoming:
    canary_id: str
    observed_at: datetime
    source: str


def import_webhook(state: State, payload: Any, *, imported_at: datetime | None = None) -> ImportResult:
    """Append unique events from a webhook payload and save the state."""
    incoming = parse_payload(payload)
    incoming.sort(key=lambda item: (item.observed_at, item.canary_id, item.source))

    known = state.canary_map()
    seen = {event.dedup_key for event in state.events}
    history = list(state.events)
    staged: list[Event] = []
    duplicates = 0
    unmatched = 0

    for item in incoming:
        dedup_key = f"{item.canary_id}|{item.source}|{_bucket(item.observed_at)}"
        if dedup_key in seen:
            duplicates += 1
            continue
        seen.add(dedup_key)
        canary = known.get(item.canary_id)
        kind = canary.kind if canary else "unknown"
        if canary is None:
            unmatched += 1
        staged.append(
            Event(
                canary_id=item.canary_id,
                kind=kind,
                observed_at=_iso_z(item.observed_at),
                source=item.source,
                severity=classify(kind, item.canary_id, item.source, history + staged, known),
                dedup_key=dedup_key,
            )
        )

    moment = imported_at or datetime.now(timezone.utc)
    state.events.extend(staged)
    state.last_import = {
        "imported": len(staged),
        "duplicates": duplicates,
        "unmatched": unmatched,
        "at": _iso_z(moment),
    }
    state.save()
    return ImportResult(imported=len(staged), duplicates=duplicates, unmatched=unmatched)


def classify(
    kind: str,
    canary_id: str,
    source: str,
    history: list[Event],
    known: dict[str, Canary],
) -> str:
    """Severity for a new unique observation."""
    if canary_id not in known:
        return "low"
    if kind in ("dns", "email"):
        return "high"
    prior_sources = {event.source for event in history if event.canary_id == canary_id}
    if source not in prior_sources:
        return "medium" if not prior_sources else "high"
    return "low"


def parse_payload(payload: Any) -> list[Incoming]:
    items = _items(payload)
    if len(items) > MAX_EVENTS:
        raise InputError("Webhook excede 1000 eventos.")
    return [_incoming(item) for item in items]


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("events"), list):
        items = payload["events"]
    elif isinstance(payload, dict):
        items = [payload]
    else:
        raise InputError("Webhook precisa ser um objeto JSON ou uma lista.")
    for item in items:
        if not isinstance(item, dict):
            raise InputError("Cada evento do webhook precisa ser um objeto.")
    return items


def _incoming(item: dict[str, Any]) -> Incoming:
    canary_id = _canary_id(item)
    if not canary_id:
        raise InputError("Evento sem canary_id.")
    observed_at = _observed_at(item)
    if observed_at is None:
        raise InputError("Evento sem observed_at.")
    return Incoming(canary_id=canary_id, observed_at=observed_at, source=_source(item))


def _canary_id(item: dict[str, Any]) -> str | None:
    for key in _ID_KEYS + _HINT_KEYS:
        token = _token_in(item.get(key))
        if token:
            return token
    for key, value in item.items():
        if key in _SOURCE_KEYS:
            continue
        token = _token_in(value)
        if token:
            return token
    return None


def _token_in(value: object) -> str | None:
    if isinstance(value, str):
        return normalize_token(value)
    return None


def load_webhook_file(path: str) -> Any:
    """Read a webhook JSON file, or stdin when path is ``-``."""
    if path == "-":
        raw = sys.stdin.buffer.read(MAX_WEBHOOK_BYTES + 1)
        return load_webhook_bytes(raw)
    file_path = Path(path)
    if not file_path.is_file():
        raise InputError(f"Webhook não encontrado: {path}")
    if file_path.stat().st_size > MAX_WEBHOOK_BYTES:
        raise InputError("Webhook excede 2 MB.")
    return load_webhook_bytes(file_path.read_bytes())


def load_webhook_text(text: str) -> Any:
    """Parse a webhook JSON string."""
    return load_webhook_bytes(text.encode("utf-8"))


def load_webhook_bytes(raw: bytes) -> Any:
    if len(raw) > MAX_WEBHOOK_BYTES:
        raise InputError("Webhook excede 2 MB.")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"Webhook não é JSON válido: {exc}") from exc
    return payload


def _observed_at(item: dict[str, Any]) -> datetime | None:
    for key in _TIME_KEYS:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return _parse_time(value)
    return None


def _source(item: dict[str, Any]) -> str:
    for key in _SOURCE_KEYS:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            text = value.strip()
            if any(ord(char) < 32 for char in text):
                raise InputError("Origem do evento inválida.")
            return text[:256]
    return "unspecified"


def _parse_time(value: str) -> datetime:
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise InputError("observed_at inválido.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _bucket(moment: datetime) -> int:
    epoch = int(moment.timestamp())
    return epoch - (epoch % DEDUP_WINDOW_SECONDS)


def _iso_z(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
