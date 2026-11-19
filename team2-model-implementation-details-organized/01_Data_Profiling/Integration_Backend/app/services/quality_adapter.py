
import pandas as pd
from datetime import datetime, timezone

from app.services.data_quality_engine import DataQualityEngine
from app.services.team1_data_quality import (
    DataQualityEngine as Team1DataQualityEngine
)


SUPPORTED_RULES = [
    "NULL_CHECK",
    "DUP_ROW",
    "INVALID_RANGE",
    "OUTLIER_IQR"
]


RULE_ID_MAPPING = {
    "VAL_NULL_001": "NULL_CHECK",
    "VAL_DUP_001": "DUP_ROW",
    "VAL_INV_001": "INVALID_RANGE",
    "VAL_OUT_001": "OUTLIER_IQR",
    "INVALID_AGE_AT_HIRE": "INVALID_RANGE"
}


def normalize_severity(severity):
    severity = str(severity).strip().upper()

    severity_mapping = {
        "BLOCKING ERROR": "CRITICAL",
        "WARNING": "MEDIUM",
        "CRITICAL": "CRITICAL",
        "HIGH": "HIGH",
        "MEDIUM": "MEDIUM",
        "LOW": "LOW"
    }

    return severity_mapping.get(severity, "MEDIUM")


def validate_rules(rules_to_apply):
    if rules_to_apply is None:
        return SUPPORTED_RULES.copy()

    unsupported_rules = [
        rule for rule in rules_to_apply
        if rule not in SUPPORTED_RULES
    ]

    if unsupported_rules:
        raise ValueError(
            f"Unsupported rules: {unsupported_rules}. "
            f"Supported rules: {SUPPORTED_RULES}"
        )

    return rules_to_apply


# Existing Team 2 Data Quality adapter
# Keeps the original Team 2 response format
def check_data_quality(
    dataset_source="app/data/sample.csv",
    dataset_name="Dataset",
    target_col=None,
    id_cols=None,
    numeric_columns=None,
    rules_to_apply=None
):
    rules_to_apply = validate_rules(rules_to_apply)

    engine = DataQualityEngine(
        file_path=str(dataset_source),
        dataset_name=dataset_name
    )

    result = engine.run_validation()

    selected_violations = [
        violation
        for violation in result["violations"]
        if violation["rule_id"] in rules_to_apply
    ]

    return {
        "dataset_name": result["dataset_name"],
        "execution_timestamp": result["execution_timestamp"],
        "total_rows_scanned": result["total_rows_scanned"],
        "status": (
            "FAILED_VALIDATION"
            if any(
                v.get("failed_count", 0) > 0
                for v in selected_violations
            )
            else "PASSED"
        ),
        "violations": selected_violations
    }


# Team 1 Data Quality adapter
# Returns the response format expected by Team 3
def check_team1_data_quality(
    dataset_source,
    dataset_name="Dataset",
    target_col=None,
    id_cols=None,
    numeric_columns=None,
    rules_to_apply=None
):
    rules_to_apply = validate_rules(rules_to_apply)

    dataset_source = str(dataset_source)

    if dataset_source.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(dataset_source)

    elif dataset_source.lower().endswith(".csv"):
        df = pd.read_csv(dataset_source)

    else:
        raise ValueError("Unsupported file format.")

    engine = Team1DataQualityEngine(
        df,
        dataset_name=dataset_name,
        target_col=target_col,
        id_cols=id_cols,
        numeric_columns=numeric_columns
    )

    result_df = engine.run_checks()

    violations = []

    for issue in result_df.to_dict(orient="records"):

        original_rule_id = str(issue.get("RuleID", ""))

        standardized_rule_id = RULE_ID_MAPPING.get(
            original_rule_id,
            original_rule_id
        )

        if standardized_rule_id not in rules_to_apply:
            continue

        failed_count = int(issue.get("AffectedRows", 0))

        if failed_count == 0:
            continue

        violations.append({
            "rule_id": standardized_rule_id,
            "column": str(issue.get("Column", "")),
            "severity": normalize_severity(
                issue.get("Severity", "MEDIUM")
            ),
            "failed_count": failed_count,
            "description": str(issue.get("Description", ""))
        })

    return {
        "dataset_name": dataset_name,
        "execution_timestamp": datetime.now(
            timezone.utc
        ).isoformat().replace("+00:00", "Z"),
        "total_rows_scanned": len(df),
        "status": (
            "FAILED_VALIDATION"
            if any(
                violation["failed_count"] > 0
                for violation in violations
            )
            else "PASSED"
        ),
        "violations": violations
    }
