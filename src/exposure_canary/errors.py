"""Exceptions for exposure_canary."""


class Error(Exception):
    """Base exception for exposure_canary."""


class InputError(Error):
    """Raised when a canary, webhook, or state file is invalid."""
