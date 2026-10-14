"""Canary and normalized event records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Canary:
    """A bait planted on an asset the operator controls."""

    id: str
    kind: str
    label: str
    asset: str
    value: str
    created_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "asset": self.asset,
            "value": self.value,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Canary:
        return cls(
            id=str(data["id"]),
            kind=str(data["kind"]),
            label=str(data["label"]),
            asset=str(data["asset"]),
            value=str(data["value"]),
            created_at=str(data["created_at"]),
        )


@dataclass(frozen=True)
class Event:
    """One unique observation of a canary."""

    canary_id: str
    kind: str
    observed_at: str
    source: str
    severity: str
    dedup_key: str

    def to_dict(self) -> dict[str, str]:
        return {
            "canary_id": self.canary_id,
            "kind": self.kind,
            "observed_at": self.observed_at,
            "source": self.source,
            "severity": self.severity,
            "dedup_key": self.dedup_key,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        return cls(
            canary_id=str(data["canary_id"]),
            kind=str(data["kind"]),
            observed_at=str(data["observed_at"]),
            source=str(data["source"]),
            severity=str(data["severity"]),
            dedup_key=str(data["dedup_key"]),
        )


@dataclass(frozen=True)
class ImportResult:
    """Counts from one webhook import."""

    imported: int
    duplicates: int
    unmatched: int

    def to_dict(self) -> dict[str, int]:
        return {
            "imported": self.imported,
            "duplicates": self.duplicates,
            "unmatched": self.unmatched,
        }
