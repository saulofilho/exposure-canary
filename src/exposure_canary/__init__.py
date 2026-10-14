"""exposure_canary package.

Iscas defensivas (URL, DNS, parte local de e-mail) para ativos que você controla.
"""

from __future__ import annotations

from .errors import Error, InputError
from .models import Canary, Event, ImportResult
from .service import State, create_canary, import_webhook, render_report
from .version import __version__

__all__ = [
    "__version__",
    "Canary",
    "Event",
    "ImportResult",
    "Error",
    "InputError",
    "State",
    "create_canary",
    "import_webhook",
    "render_report",
]
