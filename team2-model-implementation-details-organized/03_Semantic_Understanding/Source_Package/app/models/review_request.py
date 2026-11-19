
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


ProblemType = Literal[
    "binary_classification",
    "multiclass_classification",
    "regression",
    "forecasting",
    "clustering",
    "anomaly_detection",
    "recommendation",
    "review_required"
]


class ReviewRequest(BaseModel):
    """
    User review decisions based on the proposed Team 3 schema.
    """

    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1)
    goal: str | None = None
    target: str | None = None
    problem_type: ProblemType | None = None
    approved_feature_columns: list[str] | None = None

    @model_validator(mode="after")
    def validate_review_decision(self):

        if self.target is not None and not self.target.strip():
            raise ValueError("Target cannot be empty.")

        if self.goal is not None and not self.goal.strip():
            raise ValueError("Goal cannot be empty.")

        if self.approved_feature_columns is not None:
            if len(self.approved_feature_columns) != len(
                set(self.approved_feature_columns)
            ):
                raise ValueError(
                    "Duplicate feature columns are not allowed."
                )

        return self
