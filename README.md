# End-to-End Job Market Analytics Pipeline Using AWS

An AWS serverless data engineering project that ingests job postings from the Adzuna API, stores raw data in S3, transforms it with AWS Glue, queries it with Athena, and serves analytics through a Streamlit dashboard.

## Architecture

```text
Adzuna API
  -> AWS Lambda ingestion
  -> S3 raw/adzuna/                          Bronze layer
  -> AWS Glue cleaning job
  -> S3 processed/cleaned_jobs/              Silver layer
  -> AWS Glue skill extraction job
  -> S3 processed/skills_extracted/          Silver layer
  -> Athena external tables and views        Logical gold layer
  -> Streamlit dashboard
```

The AWS infrastructure was configured manually in the AWS Console. EventBridge, Glue crawler, Glue workflow orchestration, and IAM roles are part of the implemented cloud setup, while this repository stores the application code, AWS job scripts, SQL, and project documentation.

## Project Goals

- Track in-demand technical skills from job postings.
- Analyze salary trends by skill, location, company, and seniority.
- Build a practical AWS data lake pipeline using managed services.
- Provide a dashboard-ready analytics layer through Athena views.
- Keep the system simple, low-cost, and interview-ready.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Ingestion | AWS Lambda, Adzuna API, Python, requests, boto3 |
| Storage | Amazon S3 |
| Processing | AWS Glue, PySpark |
| Catalog / Metadata | AWS Glue Data Catalog, Glue Crawler |
| Query Layer | Amazon Athena |
| Orchestration | EventBridge, AWS Glue Workflow |
| Dashboard | Streamlit, PyAthena, Plotly, Pandas |
| Security | IAM roles and least-privilege access policies |

## Current Status

Completed:

- Lambda ingestion from Adzuna API.
- Raw job data landing in S3 under `raw/adzuna/YYYY/MM/DD/`.
- Glue crawler for raw JSON schema discovery.
- Glue cleaning job writing cleaned Parquet.
- Glue skill extraction job writing skill-level Parquet.
- Glue workflow connecting the ETL jobs.
- Athena database, external tables, and views.
- Streamlit dashboard that can query Athena or local CSV fallback data.

Not included as infrastructure-as-code:

- EventBridge schedule configuration.
- Glue crawler and workflow definitions.
- IAM role creation.
- Athena workgroup setup.

These were created manually in the AWS Console and are documented in [AWS_CONSOLE_SETUP.md](AWS_CONSOLE_SETUP.md).

## AWS Resources

| Resource | Value |
| --- | --- |
| AWS region | `us-east-1` |
| S3 bucket | `job-trends-pipeline-12345` |
| Athena database | `job_trends_db` |
| Athena output path | `s3://job-trends-pipeline-12345/athena-results/` |
| Raw prefix | `raw/adzuna/` |
| Cleaned jobs prefix | `processed/cleaned_jobs/` |
| Skills fact prefix | `processed/skills_extracted/` |
| Glue crawler | `adzuna-raw-crawler` |
| Glue workflow | `daily-job-trends-pipeline` |
| Glue jobs | `adzuna-cleaning-job`, `adzuna-skill-extraction-job` |

The Adzuna API endpoint currently uses the `gb` region because that endpoint returned reliable job data during testing.

## Repository Contents

```text
app.py
requirements.txt
README.md
ATHENA_SQL.md
STREAMLIT_SETUP.md
AWS_CONSOLE_SETUP.md
PRE_PUSH_CHECKLIST.md
Scripts Used in AWS/
  lambda Function script/
    lambda_function.py
  ETL jobs scripts/
    glue_job_cleaning.py
    adzuna-skill-extraction-job.py
*.csv
```

The CSV files are optional exported Athena results used for local dashboard demo mode when live Athena access is unavailable.

## Local Dashboard Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a local `.env` file from [.env.example](.env.example), then run:

```powershell
streamlit run app.py
```

For local demo mode without AWS access, set:

```text
DATA_SOURCE=csv
```

For live Athena mode, set:

```text
DATA_SOURCE=athena
```

See [STREAMLIT_SETUP.md](STREAMLIT_SETUP.md) for the full Streamlit and Athena configuration.

## Athena Analytics Layer

The project uses two processed external tables:

- `job_trends_db.cleaned_jobs`
- `job_trends_db.skills_fact`

The dashboard reads these Athena views:

- `job_trends_db.top_skills_daily`
- `job_trends_db.salary_by_skill`
- `job_trends_db.vw_skills_trend_30days`
- `job_trends_db.vw_location_salary_analysis`
- `job_trends_db.vw_company_hiring_trends`
- `job_trends_db.vw_salary_by_seniority`

Athena views are the current logical gold layer. They do not store data; they recompute results when queried. A future improvement would be a physical curated/gold Parquet layer under `curated/`.

All table and view SQL is stored in [ATHENA_SQL.md](ATHENA_SQL.md).

## Dashboard

The Streamlit dashboard provides:

- Top skills by demand.
- Demand vs salary matrix.
- Skill demand trends over time.
- Company hiring trends.
- Location salary analysis.
- Salary by seniority.
- Salary by skill data table.

The dashboard can run in two modes:

- `athena`: live query mode using PyAthena.
- `csv`: local fallback mode using exported CSV files.

## Cost And Pause Notes

The pipeline is designed around pay-per-use AWS services. At this project scale, Glue is usually the main visible cost driver, while Lambda, S3, Athena, and EventBridge remain small if usage is limited.

To pause the project without deleting it:

- Disable EventBridge schedules.
- Disable or pause Glue workflow triggers.
- Stop any active Glue workflow or crawler run.
- Keep S3, Athena tables, Glue jobs, IAM roles, Lambda code, and Streamlit code intact.

This preserves the architecture and avoids rebuilding before a demo or interview.

## Screenshots

Recommended screenshots to add before final submission:

- S3 bucket folder structure.
- Lambda successful test result.
- Glue workflow graph.
- Glue job run history.
- Athena tables and views.
- Streamlit dashboard charts.
- AWS billing/cost page showing low spend.

Store screenshots in a future `docs/screenshots/` folder and reference them from this README.

## Interview Summary

I built an end-to-end AWS job-market analytics pipeline where Lambda ingests Adzuna job postings into S3, Glue cleans and enriches the data, Athena exposes analytics tables and views, and Streamlit visualizes job-market trends such as top skills, salary patterns, company demand, location demand, and seniority-based compensation.

## Before Publishing

Read [PRE_PUSH_CHECKLIST.md](PRE_PUSH_CHECKLIST.md) before pushing to GitHub. Do not commit `.env`, real AWS credentials, Adzuna API keys, local virtual environments, or cache folders.
