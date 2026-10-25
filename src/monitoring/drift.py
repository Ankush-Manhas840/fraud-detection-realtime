"""Evidently drift report: has the data the model sees changed since the data it learned from?

Run from the project folder:
    .venv\\Scripts\\python -m src.monitoring.drift
It compares purchases before the training cut-off (what the model learned from) with purchases after it
(what the model meets later), and saves reports/drift_report.html.
"""
import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset

from src.config import ROOT, load_config
from src.features import FEATURES

COLUMNS = FEATURES + ["use_chip"]   # use_chip is not a model feature; it is here to show the online-fraud drift
SAMPLE = 50_000


def generate_drift_report(reference_df, current_df, out_path):
    """Compare current data against the training reference and save an HTML report. Returns the drift summary."""
    report = Report([DataDriftPreset()])
    result = report.run(current_data=current_df, reference_data=reference_df)
    result.save_html(str(out_path))
    return result.dict()


def main():
    config = load_config()
    df = pd.read_parquet(ROOT / config["data"]["processed_path"] / "cleaned_data.parquet", columns=COLUMNS + ["timestamp"])
    df["gap_minutes"] = df["gap_minutes"].fillna(100000)
    cutoff = pd.Timestamp(config["data"]["train_end_date"])

    # reference: the last year before the cut-off (recent training data), current: everything after it
    before = df[(df["timestamp"] < cutoff) & (df["timestamp"] >= cutoff - pd.DateOffset(years=1))]
    after = df[df["timestamp"] >= cutoff]
    reference = before[COLUMNS].sample(min(SAMPLE, len(before)), random_state=42)
    current = after[COLUMNS].sample(min(SAMPLE, len(after)), random_state=42)

    out_path = ROOT / config["monitoring"]["drift_report_dir"] / "drift_report.html"
    summary = generate_drift_report(reference, current, out_path)
    for metric in summary["metrics"]:
        name = metric["metric_name"]
        if name.startswith("ValueDrift"):
            print(f"{name:60} {metric['value']:.3f}")
    print("saved", out_path)


if __name__ == "__main__":
    main()
