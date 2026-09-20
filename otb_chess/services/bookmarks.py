"""Versioned, atomic bookmark storage. Loading never starts engines or clocks."""
import json
import logging
import os
from pathlib import Path
import tempfile

from otb_chess.bookmarks import BookmarkCollection
from otb_chess.services import settings

log = logging.getLogger(__name__)


def engine_reference_available(configuration):
    """Check known local resources, without launching or substituting an engine.

    Future engine registries can supply a resolver for profile/personality IDs.
    Unknown settings remain opaque and are never discarded.
    """
    resources = [configuration.get("executable"),
                 configuration.get("settings", {}).get("weights_path")]
    return all(Path(resource).is_file() for resource in resources if resource)


class BookmarkStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else settings.CONFIG_PATH.with_name("bookmarks.json")
        self.error = None

    def load(self, *, engine_available=engine_reference_available):
        self.error = None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return BookmarkCollection.from_dict(data, engine_available=engine_available)
        except FileNotFoundError:
            return BookmarkCollection()
        except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError) as exc:
            self.error = f"Bookmarks could not be loaded: {exc}"
            log.warning("%s (%s)", self.error, self.path)
            # Do not write here: keep the damaged/unsupported file for recovery.
            return BookmarkCollection()

    def save(self, collection):
        temporary = None
        try:
            payload = json.dumps(collection.to_dict(), ensure_ascii=False, allow_nan=False, indent=2)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix=self.path.name + ".", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            self.error = None
            return True
        except (OSError, ValueError, TypeError, RecursionError) as exc:
            self.error = f"Bookmarks could not be saved: {exc}"
            log.warning("%s (%s)", self.error, self.path)
            return False
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    log.warning("Could not remove bookmark temporary file %s", temporary)
