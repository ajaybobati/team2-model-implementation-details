
import json
from pathlib import Path

import pandas as pd
import numpy as np


CONFIG_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "quality_rule_config.json"
)


def load_domain_config(dataset_name):
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Quality configuration not found: {CONFIG_PATH}"
        )

    with open(CONFIG_PATH, "r", encoding="utf-8-sig") as file:
        config = json.load(file)

    if config.get("dataset_name") != dataset_name:
        return {}

    return config.get("rules", {}).get("column_boundaries", {})


class DataQualityEngine:

    def __init__(
        self,
        df,
        dataset_name="Dataset",
        target_col=None,
        id_cols=None,
        numeric_columns=None
    ):
        self.df = df.copy(deep=True)
        self.dataset_name = dataset_name
        self.target_col = target_col
        self.id_cols = id_cols or []
        self.numeric_columns = numeric_columns or []
        self.issues = []

        self.column_boundaries = load_domain_config(dataset_name)

    def add_issue(
        self,
        rule_id,
        category,
        severity,
        column,
        affected_count,
        description,
        recommendation
    ):
        self.issues.append({
            "Dataset": self.dataset_name,
            "RuleID": rule_id,
            "Category": category,
            "Severity": severity,
            "Column": column,
            "AffectedRows": int(affected_count),
            "Description": description,
            "Recommendation": recommendation
        })

    def run_checks(self):

        # 1. Missing-value checks
        for col in self.df.columns:
            missing_count = int(self.df[col].isnull().sum())

            if missing_count > 0:
                is_target = col == self.target_col

                self.add_issue(
                    "VAL_NULL_001",
                    "Missing Target" if is_target else "Missing Values",
                    "Blocking Error" if is_target else "Warning",
                    col,
                    missing_count,
                    f"Column '{col}' contains {missing_count} missing values.",
                    "Apply imputation or drop rows if target is missing."
                )

        # 2. Duplicate identifier checks
        for col in self.id_cols:
            if col in self.df.columns:
                duplicate_count = int(
                    self.df[col].duplicated().sum()
                )

                if duplicate_count > 0:
                    self.add_issue(
                        "VAL_DUP_001",
                        "Duplicate Identifiers",
                        "Blocking Error",
                        col,
                        duplicate_count,
                        f"Identifier column '{col}' contains {duplicate_count} duplicate entries.",
                        "Investigate primary key relationship or composite keys."
                    )

        # 3. Invalid numeric values
        for col in self.numeric_columns:
            if col not in self.df.columns:
                continue

            original = self.df[col]
            converted = pd.to_numeric(original, errors="coerce")

            invalid_mask = original.notna() & converted.isna()
            invalid_count = int(invalid_mask.sum())

            if invalid_count > 0:
                self.add_issue(
                    "RULE_INVALID_NUM_001",
                    "Invalid Numeric Values",
                    "Blocking Error",
                    col,
                    invalid_count,
                    f"Column '{col}' contains {invalid_count} non-numeric values.",
                    "Correct values to match the expected numeric data type."
                )

        # 4. Configured domain-boundary validation
        for col, limits in self.column_boundaries.items():

            if col not in self.df.columns:
                continue

            min_value = limits.get("min_value")
            max_value = limits.get("max_value")

            if min_value is None and max_value is None:
                continue

            values = pd.to_numeric(
                self.df[col], errors="coerce"
            )

            invalid_mask = values.notna() & (
                (values < min_value if min_value is not None
                 else False)
                | (values > max_value if max_value is not None
                   else False)
            )

            failed_count = int(invalid_mask.sum())

            self.add_issue(
                "VAL_INV_001",
                "Domain Boundary Validation",
                "Blocking Error" if failed_count else "Warning",
                col,
                failed_count,
                (
                    f"{failed_count} values are outside configured "
                    f"domain boundaries [{min_value}, {max_value}]."
                    if failed_count
                    else (
                        f"All values are within configured domain "
                        f"boundaries [{min_value}, {max_value}]."
                    )
                ),
                "Review values against the configured domain limits."
            )

        # 5. IQR outlier checks for continuous numeric columns
        numeric_data = self.df.select_dtypes(
            include=[np.number]
        )

        for col in numeric_data.columns:

            if col in self.id_cols:
                continue

            # Exclude binary flags from continuous numeric checks
            if col in ["SalariedFlag", "CurrentFlag"]:
                continue

            series = numeric_data[col].dropna()

            if len(series) < 5:
                continue

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

            outliers = series[
                (series < lower) | (series > upper)
            ]

            failed_count = int(len(outliers))

            self.add_issue(
                "VAL_OUT_001",
                "Statistical Outliers",
                "Warning",
                col,
                failed_count,
                (
                    f"{failed_count} statistical outliers detected "
                    f"using 1.5x IQR bounds [{lower}, {upper}]."
                    if failed_count
                    else "No statistical outliers detected using 1.5x IQR."
                ),
                "Review statistical outliers; do not automatically remove valid observations."
            )

        # 6. Age-at-hire validation
        if {"BirthDate", "HireDate"}.issubset(self.df.columns):

            birth = pd.to_datetime(
                self.df["BirthDate"], errors="coerce"
            )

            hire = pd.to_datetime(
                self.df["HireDate"], errors="coerce"
            )

            age = (
                hire.dt.year - birth.dt.year
                - (
                    (hire.dt.month < birth.dt.month)
                    | (
                        (hire.dt.month == birth.dt.month)
                        & (hire.dt.day < birth.dt.day)
                    )
                )
            )

            invalid_age = (
                birth.notna()
                & hire.notna()
                & ((age < 18) | (age > 80))
            )

            invalid_count = int(invalid_age.sum())

            if invalid_count > 0:
                self.add_issue(
                    "INVALID_AGE_AT_HIRE",
                    "Invalid Age at Hire",
                    "CRITICAL",
                    "BirthDate/HireDate",
                    invalid_count,
                    f"{invalid_count} records have an age at hire outside the 18-80 range.",
                    "Verify BirthDate and HireDate values."
                )

        return pd.DataFrame(self.issues)
