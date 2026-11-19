# Team 2 - Final API Documentation

## Project
Team 2 Profiling and Data Quality Backend API

## Technology
- Python
- FastAPI
- Pandas
- NumPy
- Pydantic
- Uvicorn

## Run the API

Install dependencies:

    pip install -r requirements.txt

Start the application from the package root:

    uvicorn main:app --reload

Open API documentation:

    http://127.0.0.1:8000/docs

Health check:

    GET /health

## Data Profiling

Endpoint:

    POST /api/v1/profiling/

Implementation and contract files are available in Data_Profiling.

## Data Quality

Endpoints:

    POST /api/v1/quality/
    POST /api/v1/quality/validate

Implementation and schemas are available in Data_Quality.

## Runtime Structure

The app folder preserves the imports used by main.py, including
the routes and services required by the application.

The dataset registry is initialized as an empty JSON array.
Upload your own test dataset through the API before using
dataset-registry-based operations.

## Important

This package excludes virtual environments, backup files,
local HR datasets, and machine-specific dataset registry entries.
