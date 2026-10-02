"""SHAP helpers: why did the model flag this transaction?"""


def get_explainer(model):
    """Build a SHAP explainer for the trained model."""
    # TODO (Oct 13): SHAP explainer.
    raise NotImplementedError


def top_reasons(explainer, x_row, k=3):
    """Return the top-k human-readable reasons for one transaction's score."""
    # TODO (Oct 13 / Oct 19): top reasons for API response.
    raise NotImplementedError
