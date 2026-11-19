
from app.utils.json_loader import (
    load_profiling_data,
    load_quality_data
)


def get_dataset_quality(dataset_id: str) -> dict:
    """
    Retrieve quality information for the selected dataset.
    """

    quality_data = load_quality_data()

    for dataset in quality_data:
        dataset_name = dataset.get("dataset", "")
        normalized_name = dataset_name.replace(".xlsx", "")

        if normalized_name == dataset_id:
            return dataset

    return {
        "dataset": dataset_id,
        "total_rows": 0,
        "issues": []
    }


def classify_column(column: dict) -> str:
    """
    Classify a column based on its inferred data type.
    """

    inferred_type = column.get("inferred_type", "unknown")

    if inferred_type == "numerical":
        return "numerical"

    if inferred_type == "categorical":
        return "categorical"

    if inferred_type == "datetime":
        return "datetime"

    return "unknown"


def calculate_target_score(column: dict, quality_issues: list) -> tuple:
    """
    Calculate a preliminary target suitability score.
    This is a heuristic, not a trained ML prediction.
    """

    score = 50
    reasons = []

    name = column.get("name", "")
    inferred_type = column.get("inferred_type", "unknown")

    if column.get("likely_identifier", False):
        return 0, ["Excluded because this column is identified as an identifier."]

    if inferred_type == "numerical":
        score += 20
        reasons.append("Numerical column can support regression or classification.")

    elif inferred_type == "categorical":
        score += 15
        reasons.append("Categorical column can support classification.")

    elif inferred_type == "datetime":
        score += 5
        reasons.append("Datetime column may be useful for time-based prediction.")

    else:
        score -= 20
        reasons.append("Column has an unsupported or unknown data type.")

    missing_pct = column.get("missing_pct", 0)

    if missing_pct > 20:
        score -= 25
        reasons.append("High percentage of missing values.")

    elif missing_pct > 0:
        score -= 5
        reasons.append("Column contains some missing values.")

    else:
        reasons.append("No missing values detected.")

    column_issues = [
        issue for issue in quality_issues
        if issue.get("affected_column") == name
        and issue.get("severity", "").lower() in ["error", "warning"]
    ]

    if column_issues:
        score -= 20
        reasons.append(
            f"{len(column_issues)} quality warning/error(s) detected."
        )

    else:
        reasons.append("No warning/error found for this column.")

    score = max(0, min(100, score))

    return score, reasons


def analyze_semantic_understanding() -> dict:
    """
    Analyze profiling and quality information.
    Generate column roles and ranked target suggestions.
    """

    profiling = load_profiling_data()

    dataset_id = profiling["dataset_reference"]["dataset_id"]
    dataset_info = profiling["dataset"]

    quality = get_dataset_quality(dataset_id)
    quality_issues = quality.get("issues", [])

    column_analysis = []
    target_candidates = []

    for column in profiling.get("columns", []):

        column_name = column.get("name")
        column_type = classify_column(column)

        is_identifier = column.get("likely_identifier", False)

        if is_identifier:
            role = "identifier"

        elif column_type == "numerical":
            role = "numerical_feature"

        elif column_type == "categorical":
            role = "categorical_feature"

        elif column_type == "datetime":
            role = "datetime_feature"

        else:
            role = "unknown"

        column_analysis.append({
            "column_name": column_name,
            "data_type": column_type,
            "column_role": role,
            "is_identifier": is_identifier,
            "missing_count": column.get("missing_count", 0),
            "missing_percentage": column.get("missing_pct", 0)
        })

        if not is_identifier:

            score, reasons = calculate_target_score(
                column,
                quality_issues
            )

            target_candidates.append({
                "target_column": column_name,
                "data_type": column_type,
                "score": score,
                "reasons": reasons,
                "approval_status": "pending"
            })

    target_candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    for rank, candidate in enumerate(target_candidates, start=1):
        candidate["rank"] = rank

    return {
        "dataset_id": dataset_id,
        "dataset_name": profiling["dataset_reference"]["name"],
        "dataset_status": profiling["status"],
        "row_count": dataset_info["row_count"],
        "column_count": dataset_info["column_count"],
        "quality_issue_count": len(quality_issues),
        "column_analysis": column_analysis,
        "target_candidates": target_candidates,
        "user_approval_required": True,
        "training_allowed": False
    }
