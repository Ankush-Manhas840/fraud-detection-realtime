"""ALL feature functions. Shared by training and live scoring (one code path, no skew)."""


def add_velocity_features(df, windows):
    """Add per-user transaction counts / amount sums over the given windows (in steps)."""
    # TODO (Oct 7): velocity features.
    raise NotImplementedError


def add_deviation_features(df):
    """Add features comparing a transaction's amount to the user's usual behaviour."""
    # TODO (Oct 8): deviation features.
    raise NotImplementedError


def add_balance_error_features(df):
    """Add features capturing mismatches between balances and the transaction amount."""
    # TODO (Oct 8): balance-error features.
    raise NotImplementedError


def build_features(df):
    """Apply every feature function and return the model-ready DataFrame."""
    # TODO (Oct 8): chain all feature functions.
    raise NotImplementedError
