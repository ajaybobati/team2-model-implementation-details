
const API_URL = "http://127.0.0.1:8000";

let currentAnalysis = null;

// 1. LOAD SEMANTIC ANALYSIS
async function analyzeDataset() {
    const message = document.getElementById("approvalMessage");

    try {
        message.textContent = "Analyzing dataset...";

        const response = await fetch(`${API_URL}/api/v1/semantic/analyze`);

        if (!response.ok) {
            throw new Error("Dataset analysis failed.");
        }

        const data = await response.json();
        currentAnalysis = data;

        displayDatasetOverview(data);
        displayColumns(data);
        displayTargetCandidates(data);
        displayFeatureOptions(data);

        validateForm();
        message.textContent = "Dataset analysis completed.";

    } catch (error) {
        message.textContent = "Error: " + error.message;
        console.error(error);
    }
}

// 2. DATASET OVERVIEW
function displayDatasetOverview(data) {
    document.getElementById("datasetId").textContent =
        data.dataset_id || "Not available";

    document.getElementById("rowCount").textContent =
        data.row_count ?? 0;

    document.getElementById("columnCount").textContent =
        data.column_count ?? 0;

    document.getElementById("qualityCount").textContent =
        data.quality_issue_count ?? 0;
}

// 3. COLUMN ANALYSIS
function displayColumns(data) {
    const table = document.getElementById("columnTable");
    table.innerHTML = "";

    const columns = data.column_analysis || [];

    columns.forEach(column => {
        const row = document.createElement("tr");

        [
            column.column_name,
            column.data_type,
            column.is_identifier ? "Yes" : "No",
            column.missing_count
        ].forEach(value => {
            const cell = document.createElement("td");
            cell.textContent = value ?? "";
            row.appendChild(cell);
        });

        table.appendChild(row);
    });
}

// 4. TARGET CANDIDATES
function displayTargetCandidates(data) {
    const table = document.getElementById("targetTable");
    const targetSelect = document.getElementById("targetSelect");

    table.innerHTML = "";
    targetSelect.innerHTML =
        '<option value="">Select Target Column</option>';

    const candidates = data.target_candidates || [];

    candidates.forEach(candidate => {
        const targetName = candidate.target_column;
        const row = document.createElement("tr");

        [
            targetName,
            candidate.data_type,
            candidate.score,
            candidate.approval_status
        ].forEach(value => {
            const cell = document.createElement("td");
            cell.textContent = value ?? "";
            row.appendChild(cell);
        });

        table.appendChild(row);

        const option = document.createElement("option");
        option.value = targetName;
        option.textContent =
            `${candidate.rank}. ${targetName} (Score: ${candidate.score})`;

        targetSelect.appendChild(option);
    });
}

// 5. FEATURE COLUMN SELECTION
function displayFeatureOptions(data) {
    const container = document.getElementById("featureOptions");
    container.innerHTML = "";

    const columns = data.column_analysis || [];

    columns.forEach(column => {
        if (column.is_identifier) return;

        const label = document.createElement("label");
        label.className = "feature-option";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = column.column_name;
        checkbox.className = "feature-checkbox";
        checkbox.addEventListener("change", validateForm);

        label.appendChild(checkbox);
        label.appendChild(
            document.createTextNode(" " + column.column_name)
        );

        container.appendChild(label);
    });
}

// 6. FORM VALIDATION
function validateForm() {
    const goal = document.getElementById("goalInput").value.trim();
    const target = document.getElementById("targetSelect").value;
    const problemType = document.getElementById("problemType").value;

    document.querySelectorAll(".feature-checkbox").forEach(checkbox => {
        if (checkbox.value === target) {
            checkbox.checked = false;
            checkbox.disabled = true;
        } else {
            checkbox.disabled = false;
        }
    });

    const selectedFeatures = Array.from(
        document.querySelectorAll(".feature-checkbox:checked")
    ).map(checkbox => checkbox.value);

    const hasValidFeatures = selectedFeatures.some(
        feature => feature !== target
    );

    document.getElementById("approveBtn").disabled =
        !goal || !target || !problemType || !hasValidFeatures;
}

// 7. SUBMIT REVIEW DECISIONS
async function submitReview() {
    const message = document.getElementById("approvalMessage");

    const datasetId =
        document.getElementById("datasetId").textContent;

    const goal = document.getElementById("goalInput").value.trim();
    const target = document.getElementById("targetSelect").value;
    const problemType = document.getElementById("problemType").value;

    const features = Array.from(
        document.querySelectorAll(".feature-checkbox:checked")
    ).map(checkbox => checkbox.value);

    if (!goal || !target || !problemType || features.length === 0) {
        message.textContent = "Please complete all review fields.";
        return;
    }

    if (features.includes(target)) {
        message.textContent =
            "Target cannot also be an approved feature.";
        return;
    }

    const requestBody = {
        dataset_id: datasetId,
        goal: goal,
        target: target,
        problem_type: problemType,
        approved_feature_columns: features
    };

    try {
        message.textContent = "Submitting review...";

        const response = await fetch(
            `${API_URL}/api/v1/semantic/review`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(requestBody)
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                typeof result.detail === "string"
                    ? result.detail
                    : JSON.stringify(result.detail)
            );
        }

        message.textContent =
            "Review submitted and saved successfully!";

        document.getElementById("approvalStatus").textContent =
            JSON.stringify(result.data, null, 4);

    } catch (error) {
        message.textContent = "Error: " + error.message;
        console.error(error);
    }
}

// 8. RETRIEVE SAVED REVIEW
async function retrieveSavedReview() {
    const message = document.getElementById("approvalMessage");

    const datasetId =
        document.getElementById("datasetId").textContent;

    try {
        message.textContent = "Retrieving saved review...";

        const response = await fetch(
            `${API_URL}/api/v1/semantic/review/${encodeURIComponent(datasetId)}`
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                typeof result.detail === "string"
                    ? result.detail
                    : JSON.stringify(result.detail)
            );
        }

        const review = result.data;

        document.getElementById("goalInput").value =
            review.goal || "";

        document.getElementById("targetSelect").value =
            review.target || "";

        document.getElementById("problemType").value =
            review.problem_type || "";

        document.querySelectorAll(".feature-checkbox").forEach(checkbox => {
            checkbox.checked =
                (review.approved_feature_columns || [])
                    .includes(checkbox.value);
        });

        validateForm();

        message.textContent =
            "Saved review retrieved successfully!";

        document.getElementById("approvalStatus").textContent =
            JSON.stringify(review, null, 4);

    } catch (error) {
        message.textContent = "Error: " + error.message;
        console.error(error);
    }
}

// 9. TEAM 1 SEMANTIC HANDOFF
async function generateSemanticHandoff() {
    const message = document.getElementById("handoffMessage");
    const datasetId =
        document.getElementById("datasetId").textContent;

    if (!datasetId || datasetId === "Loading...") {
        message.textContent = "Please analyze the dataset first.";
        return;
    }

    try {
        message.textContent = "Generating Team 1 semantic handoff...";

        const response = await fetch(
            `${API_URL}/api/v1/semantic/handoff/${encodeURIComponent(datasetId)}`
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                typeof result.detail === "string"
                    ? result.detail
                    : JSON.stringify(result.detail)
            );
        }

        const data = result.data;

        displayHandoffResults(data);

        message.textContent =
            "Team 1 semantic handoff generated successfully.";

    } catch (error) {
        message.textContent = "Handoff Error: " + error.message;
        console.error(error);
    }
}

// 10. DISPLAY TEAM 1 RESULTS
function displayHandoffResults(data) {
    document.getElementById("handoffTarget").textContent =
        data.target || "Not available";

    document.getElementById("handoffProblemType").textContent =
        data.problem_type || "Not available";

    const confidence = Number(data.confidence);

    document.getElementById("handoffConfidence").textContent =
        Number.isFinite(confidence)
            ? `${(confidence * 100).toFixed(1)}%`
            : "Not available";

    document.getElementById("handoffStatus").textContent =
        data.status || "Not available";

    // Approved features
    const featuresContainer =
        document.getElementById("handoffFeatures");

    featuresContainer.innerHTML = "";

    const features = data.approved_feature_columns || [];

    if (features.length === 0) {
        featuresContainer.textContent = "No approved features.";
    } else {
        const list = document.createElement("ul");

        features.forEach(feature => {
            const item = document.createElement("li");
            item.textContent = feature;
            list.appendChild(item);
        });

        featuresContainer.appendChild(list);
    }

    // Warnings
    const warningsContainer =
        document.getElementById("handoffWarnings");

    warningsContainer.innerHTML = "";

    const warnings = data.warnings || [];

    if (warnings.length === 0) {
        warningsContainer.textContent = "No warnings reported.";
    } else {
        const list = document.createElement("ul");

        warnings.forEach(warning => {
            const item = document.createElement("li");
            item.textContent = warning;
            list.appendChild(item);
        });

        warningsContainer.appendChild(list);
    }

    // Preprocessing recommendations
    const preprocessingContainer =
        document.getElementById("handoffPreprocessing");

    preprocessingContainer.innerHTML = "";

    const actions = data.preprocessing_actions || [];

    if (actions.length === 0) {
        preprocessingContainer.textContent =
            "No preprocessing recommendations available.";
    } else {
        const list = document.createElement("ul");

        actions.forEach(action => {
            const item = document.createElement("li");

            item.textContent =
                typeof action === "string"
                    ? action
                    : JSON.stringify(action);

            list.appendChild(item);
        });

        preprocessingContainer.appendChild(list);
    }

    // Complete raw response
    document.getElementById("handoffRawResult").textContent =
        JSON.stringify(data, null, 4);
}

// 11. BUTTON EVENTS
document.getElementById("approveBtn")
    .addEventListener("click", submitReview);

document.getElementById("retrieveBtn")
    .addEventListener("click", retrieveSavedReview);

document.getElementById("analyzeBtn")
    .addEventListener("click", analyzeDataset);

document.getElementById("handoffBtn")
    .addEventListener("click", generateSemanticHandoff);

document.getElementById("goalInput")
    .addEventListener("input", validateForm);

document.getElementById("targetSelect")
    .addEventListener("change", validateForm);

document.getElementById("problemType")
    .addEventListener("change", validateForm);

// 12. INITIALIZE DASHBOARD
analyzeDataset();

