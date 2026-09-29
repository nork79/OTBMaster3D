"""Stable engine families and content-addressed configuration identities.

Paths and display labels are locators/presentation, never engine identities.
Unknown engines use executable content, so renaming or moving a binary is safe.
Profiles identify settings, not translated preset labels. Explicit profile IDs
from a future registry remain supported by the bookmark schema.
"""
import hashlib
import json
from pathlib import Path
import re

ENGINE_IDS = {"stockfish": "stockfish", "fairy-stockfish": "fairy-stockfish", "rodent": "rodent"}


def _digest_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def identify_engine(name, executable):
    """Use UCI-reported family, with a binary fingerprint for unknown engines."""
    for family in ("fairy-stockfish", "stockfish", "rodent"):
        if re.match(r"^" + family + r"(?:\b|\d)", name or "", re.IGNORECASE):
            return ENGINE_IDS[family]
    return "uci:sha256:" + _digest_file(executable)


def _resources(value):
    if isinstance(value, dict):
        return {key: _resources(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resources(item) for item in value]
    if isinstance(value, str):
        try:
            if Path(value).is_file():
                return {"resource_sha256": _digest_file(value)}
        except OSError:
            pass
    return value


def profile_identifier(configuration):
    """Versioned fingerprint of effective settings, independent of display names.

    Custom resource options
    are fingerprinted by content when available. Saved IDs remain valid when a
    referenced resource is subsequently unavailable (never recompute on load).
    """
    settings = dict(configuration.get("settings", {}))
    payload = {"engine_id": configuration["engine_id"], "settings": _resources(settings),
               "elo": configuration.get("elo"), "style": configuration.get("style", "Balanced")}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return configuration["engine_id"] + ":profile:v1:" + hashlib.sha256(encoded).hexdigest()
