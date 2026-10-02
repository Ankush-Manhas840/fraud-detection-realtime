"""Load raw PaySim data and split it by time (never randomly)."""


def load_raw():
    """Read data/raw/paysim.csv into a DataFrame using the path from config."""
    # TODO (Oct 3): load the CSV for EDA.
    raise NotImplementedError


def time_based_split(df, train_end_step):
    """Return (train, test): rows with step <= train_end_step go to train, the rest to test."""
    # TODO (Oct 6): split by `step` to avoid leakage.
    raise NotImplementedError
