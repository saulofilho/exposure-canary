"""Build URL, DNS, and email-local-part canaries."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .errors import InputError
from .models import Canary

KINDS = ("url", "dns", "email")
_HOST = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_TOKEN = re.compile(r"cn-?([0-9a-f]{16})")


def new_token_id() -> str:
    """Return a canary id: ``cn`` plus 16 hex characters."""
    return "cn" + secrets.token_hex(8)


def normalize_token(value: str) -> str | None:
    """Extract a canary id from a URL, DNS name, email, or bare token."""
    match = _TOKEN.search(value.lower())
    if not match:
        return None
    return "cn" + match.group(1)


def build_canary(
    *,
    kind: str,
    label: str,
    asset: str,
    owned: bool,
    collector: str | None = None,
    zone: str | None = None,
    domain: str | None = None,
    now: datetime | None = None,
    token_id: str | None = None,
) -> Canary:
    """Validate inputs and return a canary. Does not persist it."""
    if owned is not True:
        raise InputError("Confirme que o ativo é seu com owned=true.")

    normalized_kind = (kind or "").strip().lower()
    if normalized_kind not in KINDS:
        raise InputError("Tipo de isca deve ser url, dns ou email.")

    clean_label = _clean_text(label, "Rótulo", 80)
    clean_asset = _clean_text(asset, "Ativo", 120)
    canary_id = token_id or new_token_id()
    if normalize_token(canary_id) != canary_id:
        raise InputError("Id de isca inválido.")

    if normalized_kind == "url":
        if not collector or not str(collector).strip():
            raise InputError("Isca URL precisa de collector https.")
        value = f"{_valid_collector(collector)}/c/{canary_id}"
    elif normalized_kind == "dns":
        if not zone or not str(zone).strip():
            raise InputError("Isca DNS precisa de zone.")
        value = f"{canary_id}.{_valid_hostname(zone, 'Zona DNS')}"
    else:
        if not domain or not str(domain).strip():
            raise InputError("Isca de e-mail precisa de domain.")
        value = f"cn-{canary_id[2:]}@{_valid_hostname(domain, 'Domínio de e-mail')}"

    moment = now or datetime.now(timezone.utc)
    return Canary(
        id=canary_id,
        kind=normalized_kind,
        label=clean_label,
        asset=clean_asset,
        value=value,
        created_at=_iso_z(moment),
    )


def _clean_text(value: object, field: str, limit: int) -> str:
    if not isinstance(value, str):
        raise InputError(f"{field} precisa ser texto.")
    text = value.strip()
    if not text or len(text) > limit or any(ord(char) < 32 for char in text):
        raise InputError(f"{field} inválido.")
    return text


def _valid_hostname(value: str, field: str) -> str:
    host = value.strip().lower().rstrip(".")
    if not _HOST.match(host):
        raise InputError(f"{field} inválido.")
    return host


def _valid_collector(value: str) -> str:
    parsed = urlsplit(value.strip())
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or not host
        or (host != "localhost" and not _is_ipv4(host) and not _HOST.match(host))
    ):
        raise InputError("Coletor precisa ser uma URL https com host.")
    path = parsed.path.rstrip("/")
    return f"https://{parsed.netloc}{path}"


def _is_ipv4(host: str) -> bool:
    parts = host.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit() or (len(part) > 1 and part.startswith("0")):
            return False
        number = int(part)
        if number > 255:
            return False
    return True


def _iso_z(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
