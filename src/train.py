"""Trains models and logs runs to MLflow."""


def train_baseline():
    """Logistic Regression with class_weight."""
    # TODO (Oct 4): baseline model.
    raise NotImplementedError


def train_xgboost():
    """XGBoost with scale_pos_weight."""
    # TODO (Oct 9): XGBoost model.
    raise NotImplementedError


def train_lightgbm():
    """LightGBM model."""
    # TODO (Oct 10): LightGBM model.
    raise NotImplementedError


def train_isolation_forest():
    """Isolation Forest (unsupervised) for comparison."""
    # TODO (Oct 12): Isolation Forest.
    raise NotImplementedError


def main():
    """Train all models, log to MLflow, register the best one."""
    # TODO (Oct 14-15): MLflow tracking and registry.
    raise NotImplementedError


if __name__ == "__main__":
    main()
