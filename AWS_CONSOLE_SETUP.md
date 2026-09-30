# AWS Console Setup

This project was built using AWS Console configuration rather than Terraform, CloudFormation, or CDK. This document records the deployed resources and how they connect.

## Region

Main AWS region:

```text
us-east-1
```

## S3

Bucket:

```text
job-trends-pipeline-12345
```

Main prefixes:

```text
raw/adzuna/
processed/cleaned_jobs/
processed/skills_extracted/
curated/
scripts/
athena-results/
```

Layer mapping:

- `raw/adzuna/`: Bronze layer with raw Adzuna JSON.
- `processed/cleaned_jobs/`: Silver layer with cleaned job records.
- `processed/skills_extracted/`: Silver layer with one row per extracted skill.
- `curated/`: Reserved for a future physical gold layer.
- Athena views currently act as the logical gold layer.

## Lambda Ingestion

Script:

```text
Scripts Used in AWS/lambda Function script/lambda_function.py
```

Runtime:

```text
Python 3.11
```

Purpose:

- Calls the Adzuna API.
- Uses the `gb` Adzuna endpoint.
- Fetches software engineer job postings.
- Writes raw JSON to `raw/adzuna/YYYY/MM/DD/`.

Required Lambda environment variables:

```text
S3_BUCKET
ADZUNA_APP_ID
ADZUNA_APP_KEY
```

Packaging note:

- `requests` is not included in the default Lambda runtime.
- The deployed Lambda package must include `requests` or use a Lambda layer that provides it.

## EventBridge

EventBridge is used as the schedule trigger for the ingestion Lambda.

Purpose:

- Starts the ingestion automatically.
- Keeps raw data landing in S3 without manual execution.

The exact schedule expression is managed in AWS Console.

## Glue Crawler

Crawler:

```text
adzuna-raw-crawler
```

Purpose:

- Crawls `raw/adzuna/`.
- Discovers the raw JSON schema.
- Creates or updates the raw catalog table.

Raw catalog table:

```text
adzuna_raw_adzuna
```

The crawler is useful for metadata visibility and debugging. It is not the transformation engine, and the Glue ETL jobs can read S3 files directly.

## Glue ETL Jobs

Cleaning job:

```text
adzuna-cleaning-job
```

Script:

```text
Scripts Used in AWS/ETL jobs scripts/glue_job_cleaning.py
```

Behavior:

- Reads raw JSON from `raw/adzuna/`.
- Selects and normalizes job fields.
- Computes `salary_avg`.
- Removes rows without title or description.
- Drops duplicates by `job_id`.
- Writes Parquet to `processed/cleaned_jobs/YYYY/MM/DD/`.

Skill extraction job:

```text
adzuna-skill-extraction-job
```

Script:

```text
Scripts Used in AWS/ETL jobs scripts/adzuna-skill-extraction-job.py
```

Behavior:

- Reads cleaned Parquet from `processed/cleaned_jobs/`.
- Combines job title and description.
- Extracts known skills using dictionary and regex matching.
- Explodes skills to one row per skill.
- Writes Parquet to `processed/skills_extracted/`.

These Glue scripts require the AWS Glue/Spark runtime and are not intended to run as normal local Python scripts.

## Glue Workflow

Workflow:

```text
daily-job-trends-pipeline
```

Sequence:

```text
Schedule trigger
  -> adzuna-cleaning-job
  -> conditional trigger on success
  -> adzuna-skill-extraction-job
```

Purpose:

- Automates ETL sequencing.
- Ensures skill extraction runs only after cleaning completes successfully.

## Athena

Database:

```text
job_trends_db
```

Query result location:

```text
s3://job-trends-pipeline-12345/athena-results/
```

Processed tables:

```text
cleaned_jobs
skills_fact
```

Dashboard views:

```text
top_skills_daily
salary_by_skill
vw_skills_trend_30days
vw_location_salary_analysis
vw_company_hiring_trends
vw_salary_by_seniority
```

The table and view SQL is documented in [ATHENA_SQL.md](ATHENA_SQL.md).

## IAM Responsibilities

Lambda execution role:

- Write raw job data to S3.
- Write logs to CloudWatch.

Glue service role:

- Read raw S3 data.
- Write processed S3 data.
- Access Glue Data Catalog.
- Write logs to CloudWatch.

EventBridge permissions:

- Invoke the Lambda function or start scheduled workflow actions, depending on the configured schedule target.

Streamlit IAM user or role:

- Start and read Athena query results.
- Read Glue catalog metadata.
- Read processed S3 data.
- Write Athena query results to the configured results prefix.

Use least-privilege permissions and do not use the AWS root account for routine project operations.
