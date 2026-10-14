"""JSON state directory for canaries and normalized events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import InputError
from .models import Canary, Event

STATE_VERSION = 1


class State:
    """Persists canaries and events in ``<directory>/state.json``."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.path = directory / "state.json"
        self.canaries: list[Canary] = []
        self.events: list[Event] = []
        self.last_import: dict[str, Any] | None = None

    @classmethod
    def load(cls, directory: str | Path) -> State:
        path = Path(directory)
        if path.exists() and not path.is_dir():
            raise InputError("state precisa ser um diretório.")
        state = cls(path)
        if not state.path.exists():
            return state
        if not state.path.is_file():
            raise InputError("state.json precisa ser um arquivo.")
        try:
            data = json.loads(state.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise InputError(f"state.json inválido: {exc}") from exc
        if not isinstance(data, dict) or data.get("version") != STATE_VERSION:
            raise InputError("state.json em versão desconhecida.")
        try:
            state.canaries = [Canary.from_dict(item) for item in _expect_list(data, "canaries")]
            state.events = [Event.from_dict(item) for item in _expect_list(data, "events")]
        except (KeyError, TypeError) as exc:
            raise InputError("state.json com registro incompleto.") from exc
        last_import = data.get("last_import")
        if last_import is not None and not isinstance(last_import, dict):
            raise InputError("state.json com last_import inválido.")
        state.last_import = last_import
        return state

    def save(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "version": STATE_VERSION,
            "canaries": [canary.to_dict() for canary in self.canaries],
            "events": [event.to_dict() for event in self.events],
        }
        if self.last_import is not None:
            payload["last_import"] = self.last_import
        encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(self.path)

    def canary_map(self) -> dict[str, Canary]:
        return {canary.id: canary for canary in self.canaries}


def _expect_list(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        raise InputError(f"state.json sem lista {key}.")
    for item in value:
        if not isinstance(item, dict):
            raise InputError(f"state.json com item inválido em {key}.")
    return value
