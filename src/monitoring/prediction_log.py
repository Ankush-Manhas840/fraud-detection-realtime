"""Writes every prediction to SQLite."""


def init_db():
    """Create the predictions table if it does not exist."""
    # TODO (Oct 28): SQLite prediction log.
    raise NotImplementedError


def log_prediction(*args, **kwargs):
    """Insert one prediction (input, score, decision, model version, timestamp)."""
    # TODO (Oct 28)
    raise NotImplementedError
