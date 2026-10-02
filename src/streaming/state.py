"""Per-user recent-transaction state (dict first, Redis later)."""


class UserState:
    def update(self, txn):
        """Record a new transaction for its user."""
        # TODO (Oct 23): in-memory dict. (Oct 27): move to Redis.
        raise NotImplementedError

    def get_features(self, user):
        """Return live features (e.g. velocity) for the user."""
        # TODO (Oct 23 / Oct 27)
        raise NotImplementedError
