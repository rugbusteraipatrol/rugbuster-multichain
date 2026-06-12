#!/usr/bin/env python3
"""
analyze.py - RugBuster Backtest Analyzer

Compares predicted risk labels against actual token outcomes,
computes classification metrics (Precision, Recall, Accuracy, FPR),
and exports the findings to TXT and CSV reports.
"""

from __future__ import annotations

import sqlite3
import pandas as pd

# Constants
DB_NAME = "rugbuster_backtest.db"
REPORT_TXT = "backtest_report.txt"
RESULTS_CSV = "backtest_results.csv"


def calculate_metrics(tp: int, fp: int, fn: int, tn: int) -> dict[str, float]:
    """Calculate evaluation metrics safely handling division by zero."""
    precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0.0
    recall = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0.0
    accuracy = ((tp + tn) / (tp + tn + fp + fn)) * 100 if (tp + tn + fp + fn) > 0 else 0.0
    fpr = (fp / (fp + tn)) * 100 if (fp + tn) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "accuracy": accuracy,
        "fpr": fpr
    }


def main() -> None:
    print("[*] Starting RugBuster Backtest Analyzer")

    # Connect and load data
    conn = sqlite3.connect(DB_NAME)
    
    # Query only predictions with api_status='ok' and concrete outcomes (RUGGED/SURVIVED)
    query = """
        SELECT id, chain, token_address, token_symbol, scan_date,
               predicted_label, predicted_risk, actual_outcome, outcome_checked_at
        FROM predictions
        WHERE api_status = 'ok' AND actual_outcome IN ('RUGGED', 'SURVIVED')
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    total_records = len(df)
    print(f"[*] Loaded {total_records} completed backtest records from DB.")

    if total_records == 0:
        print("[!] No records available for analysis yet. Run collect.py and check_outcome.py first.")
        return

    # Filter by prediction type
    danger_df = df[df["predicted_label"] == "DANGER"]
    good_df = df[df["predicted_label"] == "GOOD"]
    warn_df = df[df["predicted_label"] == "WARN"]

    # Compute Confusion Matrix parts
    tp = len(danger_df[danger_df["actual_outcome"] == "RUGGED"])
    fp = len(danger_df[danger_df["actual_outcome"] == "SURVIVED"])
    fn = len(good_df[good_df["actual_outcome"] == "RUGGED"])
    tn = len(good_df[good_df["actual_outcome"] == "SURVIVED"])

    # Calculate metrics
    metrics = calculate_metrics(tp, fp, fn, tn)

    # Collect details of errors
    false_positives = danger_df[danger_df["actual_outcome"] == "SURVIVED"][["token_address", "token_symbol", "predicted_risk"]]
    false_negatives = good_df[good_df["actual_outcome"] == "RUGGED"][["token_address", "token_symbol", "predicted_risk"]]

    # Collect WARN token stats
    total_warn = len(warn_df)
    warn_rugged = len(warn_df[warn_df["actual_outcome"] == "RUGGED"])
    warn_survived = len(warn_df[warn_df["actual_outcome"] == "SURVIVED"])
    warn_rug_ratio = (warn_rugged / total_warn) * 100 if total_warn > 0 else 0.0

    # Build report text
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append(" RUGBUSTER BACKTEST PERFORMANCE REPORT")
    report_lines.append("=" * 60)
    report_lines.append(f"Total analyzed tokens: {total_records}")
    report_lines.append(f"  - Predicted DANGER: {len(danger_df)}")
    report_lines.append(f"  - Predicted GOOD: {len(good_df)}")
    report_lines.append(f"  - Predicted WARN: {len(warn_df)}")
    report_lines.append("-" * 60)
    
    report_lines.append("CONFUSION MATRIX:")
    report_lines.append(f"                    Stvarno RUGGED   Stvarno SURVIVED")
    report_lines.append(f"Predvideli DANGER        {tp:<16} {fp:<16} (TP / FP)")
    report_lines.append(f"Predvideli GOOD          {fn:<16} {tn:<16} (FN / TN)")
    report_lines.append("-" * 60)

    report_lines.append("METRICS:")
    report_lines.append(f"  - Precision (Tačnost DANGER): {metrics['precision']:.2f}%")
    report_lines.append(f"  - Recall (Odziv DANGER):     {metrics['recall']:.2f}%")
    report_lines.append(f"  - Accuracy (Ukupna tačnost):  {metrics['accuracy']:.2f}%")
    report_lines.append(f"  - False Positive Rate:        {metrics['fpr']:.2f}%")
    report_lines.append("-" * 60)

    report_lines.append("WARN TOKEN CALIBRATION:")
    report_lines.append(f"  - Total WARN tokens: {total_warn}")
    report_lines.append(f"  - Rugged:   {warn_rugged} ({warn_rug_ratio:.1f}%)")
    report_lines.append(f"  - Survived: {warn_survived} ({100.0 - warn_rug_ratio if total_warn > 0 else 0.0:.1f}%)")
    report_lines.append("-" * 60)

    report_lines.append("FALSE POSITIVES (Zvali DANGER, a preživeli):")
    if len(false_positives) == 0:
        report_lines.append("  (None)")
    else:
        for _, row in false_positives.iterrows():
            report_lines.append(f"  - {row['token_address']} ({row['token_symbol']}) | Risk Score: {row['predicted_risk']}")
    report_lines.append("-" * 60)

    report_lines.append("FALSE NEGATIVES (Zvali GOOD, a rugovali):")
    if len(false_negatives) == 0:
        report_lines.append("  (None)")
    else:
        for _, row in false_negatives.iterrows():
            report_lines.append(f"  - {row['token_address']} ({row['token_symbol']}) | Risk Score: {row['predicted_risk']}")
    report_lines.append("=" * 60)

    # Print to terminal
    report_content = "\n".join(report_lines)
    print(report_content)

    # Save TXT report
    with open(REPORT_TXT, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"[+] Saved TXT report to: {REPORT_TXT}")

    # Save CSV results
    df.to_csv(RESULTS_CSV, index=False)
    print(f"[+] Saved CSV results to: {RESULTS_CSV}")


if __name__ == "__main__":
    main()
