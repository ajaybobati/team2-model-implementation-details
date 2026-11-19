
from app.services.profiling_adapter import profile_sample_dataset
from app.services.quality_adapter import check_data_quality


def run_dataset_services(
    dataset_source,
    dataset_id,
    request_id=None,
    dataset_name=None,
    options=None,
    metadata=None,
    target_col=None,
    id_cols=None
):
    options = options or {}
    metadata = metadata or {}

    dataset_context = {
        "dataset_id": dataset_id,
        "dataset_name": dataset_name or dataset_id,
        "source_type": "file"
    }

    # 1. Run Profiling Service
    try:
        profiling_result = profile_sample_dataset(
            dataset_source=dataset_source,
            dataset_id=dataset_id,
            request_id=request_id,
            options=options,
            metadata={
                **metadata,
                "name": dataset_name or dataset_id
            }
        )

    except Exception:
        profiling_result = {
            "status": "failed",
            "columns": [],
            "errors": [{
                "code": "PROFILING_SERVICE_ERROR",
                "message": "Profiling service execution failed."
            }]
        }

    # 2. Get numeric columns from profiling output
    profiled_columns = profiling_result.get("columns", [])

    numeric_columns = [
        column["name"]
        for column in profiled_columns
        if column.get("inferred_type") == "numerical"
        and not column.get("likely_identifier", False)
    ]

    # 3. Run Data Quality Service
    try:
        quality_result = check_data_quality(
            dataset_source=dataset_source,
            dataset_name=dataset_name or dataset_id,
            target_col=target_col,
            id_cols=id_cols,
            numeric_columns=numeric_columns
        )

    except Exception:
        quality_result = {
            "summary": {
                "total_violations": 0,
                "status": "FAILED_VALIDATION"
            },
            "is_source_modified": False,
            "violations": [],
            "errors": [{
                "code": "QUALITY_SERVICE_ERROR",
                "message": "Data quality service execution failed."
            }]
        }

    # 4. Normalize service statuses
    profiling_status = str(
        profiling_result.get("status", "failed")
    ).lower()

    quality_summary = quality_result.get("summary", {})

    quality_status_value = str(
        quality_summary.get("status", "FAILED_VALIDATION")
    ).upper()

    if quality_result.get("errors"):
        quality_status = "failed"

    elif quality_status_value == "FAILED_VALIDATION":
        quality_status = "warning"

    elif quality_status_value == "PASSED":
        quality_status = "success"

    else:
        quality_status = "warning"

    failed_count = sum([
        profiling_status == "failed",
        quality_status == "failed"
    ])

    if failed_count == 2:
        overall_status = "failed"

    elif failed_count == 1:
        overall_status = "partial_success"

    elif "warning" in [profiling_status, quality_status]:
        overall_status = "warning"

    else:
        overall_status = "success"

    quality_issue_count = quality_summary.get(
        "total_violations", 0
    )

    # 5. Return combined response
    return {
        "dataset_context": dataset_context,

        "status": overall_status,

        "service_status": {
            "profiling": profiling_status,
            "quality": quality_status,
            "semantic_analysis": "not_configured"
        },

        "downstream_context": {
            "profiling_output_available": profiling_status != "failed",
            "quality_findings_available": quality_status != "failed",
            "semantic_output_available": False,
            "quality_issue_count": quality_issue_count
        },

        "profiling": profiling_result,

        "quality": quality_result,

        "semantic_analysis": {
            "status": "not_configured",
            "message": (
                "Semantic Analysis service/API contract "
                "is not yet available for integration."
            )
        }
    }
