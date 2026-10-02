"""Metrics, PR-AUC and threshold tuning. Never judge by accuracy."""


def compute_metrics(y_true, y_score, threshold):
    """Return precision, recall, PR-AUC and confusion matrix at the given threshold."""
    # TODO (Oct 5): evaluation metrics.
    raise NotImplementedError


def tune_threshold(y_true, y_score, cost_fn, cost_fp):
    """Pick the threshold that minimises total cost (false negatives vs false positives)."""
    # TODO (Oct 11): cost-based threshold tuning.
    raise NotImplementedError
