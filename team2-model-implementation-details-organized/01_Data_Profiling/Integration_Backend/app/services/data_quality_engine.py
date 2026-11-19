import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List


class DataQualityEngine:

    def __init__(self, file_path: str, dataset_name: str):
        self.file_path = file_path
        self.dataset_name = dataset_name
        self.df = self._load_data()

    def _load_data(self) -> pd.DataFrame:

        suffix = self.file_path.lower()

        if suffix.endswith((".xlsx", ".xls")):
            xls = pd.ExcelFile(self.file_path)
            sheet = xls.sheet_names[0]
            return pd.read_excel(
                self.file_path,
                sheet_name=sheet
            )

        elif suffix.endswith(".csv"):
            return pd.read_csv(self.file_path)

        else:
            raise ValueError("Unsupported file format.")

    def run_validation(self) -> Dict[str, Any]:

        violations: List[Dict[str, Any]] = []
        total_rows = len(self.df)

        # 1. NULL CHECK
        for col in self.df.columns:

            null_count = int(self.df[col].isnull().sum())

            if null_count > 0:
                violations.append({
                    "rule_id": "NULL_CHECK",
                    "column": col,
                    "severity": "HIGH",
                    "failed_count": null_count,
                    "description": f"Missing values detected in {col}."
                })

        # 2. DUPLICATE ROW CHECK
        dup_count = int(self.df.duplicated().sum())

        if dup_count > 0:
            violations.append({
                "rule_id": "DUP_ROW",
                "column": "ALL_COLUMNS",
                "severity": "HIGH",
                "failed_count": dup_count,
                "description": "Duplicate rows detected in the dataset."
            })

        # 3. INVALID RANGE CHECK
        # Team 1 sample: VacationHours must be between 0 and 99
        if "VacationHours" in self.df.columns:

            values = pd.to_numeric(
                self.df["VacationHours"],
                errors="coerce"
            )

            invalid_count = int(
                ((values < 0) | (values > 99)).sum()
            )

            if invalid_count > 0:
                violations.append({
                    "rule_id": "INVALID_RANGE",
                    "column": "VacationHours",
                    "severity": "MEDIUM",
                    "failed_count": invalid_count,
                    "description": (
                        "VacationHours values must be between 0 and 99."
                    )
                })

        # 4. OUTLIER CHECK USING IQR
        numeric_columns = [
             col for col in self.df.select_dtypes(
             include=["number"]
          ).columns
             if col.lower() not in [
         "salariedflag",
         "organizationlevel"
    ]
]
      

        for col in numeric_columns:

            # Skip identifier columns
            if "id" in col.lower():
                continue

            values = pd.to_numeric(
                self.df[col],
                errors="coerce"
            ).dropna()

            if len(values) < 4:
                continue

            q1 = values.quantile(0.25)
            q3 = values.quantile(0.75)
            iqr = q3 - q1

            lower_bound = q1 - (1.5 * iqr)
            upper_bound = q3 + (1.5 * iqr)

            outlier_count = int(
                (
                    (values < lower_bound) |
                    (values > upper_bound)
                ).sum()
            )

            if outlier_count > 0:
                violations.append({
                    "rule_id": "OUTLIER_IQR",
                    "column": col,
                    "severity": "LOW",
                    "failed_count": outlier_count,
                    "description": (
                        f"{outlier_count} statistical outliers "
                        f"detected in {col} using IQR method."
                    )
                })

        status = (
            "FAILED_VALIDATION"
            if violations
            else "PASSED"
        )

        return {
            "dataset_name": self.dataset_name,
            "execution_timestamp": datetime.now(
                timezone.utc
            ).isoformat().replace("+00:00", "Z"),
            "total_rows_scanned": total_rows,
            "status": status,
            "violations": violations
        }