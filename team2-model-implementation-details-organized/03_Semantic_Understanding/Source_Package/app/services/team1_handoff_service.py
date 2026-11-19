
import sys
from pathlib import Path

# Backend project directories
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

# Team 1 engine directory
TEAM1_ENGINE_DIR = (
    BASE_DIR.parent / "team1_engine" / "semantic_detection"
)

# Add Team 1 engine to Python import path
if str(TEAM1_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(TEAM1_ENGINE_DIR))

# Import actual Team 1 functions
from run_detection import (
    run_detection,
    review_decisions_to_arguments
)

# Import Team 2 review service
from app.services.review_service import get_saved_review_decision


PROFILE_DIR = DATA_DIR
QUALITY_FILE = DATA_DIR / "input_quality_all_tables.json"


def generate_handoff(dataset_id: str) -> dict:
    """
    Generate semantic handoff using Team 1 engine
    and Team 2 saved review decisions.
    """

    # Check required files
    if not QUALITY_FILE.exists():
        raise FileNotFoundError("Quality report not found.")

    # Find profiling files
    profile_files = sorted(
        PROFILE_DIR.glob("*.profile.json")
    )

    if not profile_files:
        raise FileNotFoundError(
            "No profiling JSON files found."
        )

    # Retrieve saved review decision
    review_decision = get_saved_review_decision(dataset_id)

    # Convert review payload into Team 1 arguments
    review_arguments = review_decisions_to_arguments(
        review_decision
    )

    # Execute actual Team 1 detection engine
    results = run_detection(
        profiles=profile_files,
        quality=str(QUALITY_FILE),
        **review_arguments
    )

    # Find requested dataset result
    for result in results:
        if result.get("dataset_id") == dataset_id:
            return result

    raise ValueError(
        f"No handoff result generated for dataset: {dataset_id}"
    )
