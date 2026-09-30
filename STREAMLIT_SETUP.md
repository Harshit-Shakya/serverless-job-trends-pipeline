# Streamlit And Athena Setup

The dashboard in `app.py` supports two data modes:

- `athena`: live queries against Athena views.
- `csv`: local demo mode using exported CSV files in the repo.

## Local Environment

Create a `.env` file from `.env.example`:

```text
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
ATHENA_DATABASE=job_trends_db
ATHENA_WORKGROUP=primary
ATHENA_OUTPUT_S3=s3://job-trends-pipeline-12345/athena-results/
DATA_SOURCE=athena
CACHE_TTL_SECONDS=120
```

Install and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

For local CSV demo mode, set:

```text
DATA_SOURCE=csv
```

## Streamlit Cloud Secrets

If deploying outside AWS, create a restricted IAM user for the dashboard and store credentials in Streamlit Cloud secrets:

```toml
AWS_ACCESS_KEY_ID = "YOUR_KEY"
AWS_SECRET_ACCESS_KEY = "YOUR_SECRET"
AWS_DEFAULT_REGION = "us-east-1"
ATHENA_DATABASE = "job_trends_db"
ATHENA_WORKGROUP = "primary"
ATHENA_OUTPUT_S3 = "s3://job-trends-pipeline-12345/athena-results/"
DATA_SOURCE = "athena"
CACHE_TTL_SECONDS = "120"
```

Never place real credentials in the repository.

## Athena Views Used By The App

The dashboard expects these views to exist:

- `job_trends_db.top_skills_daily`
- `job_trends_db.salary_by_skill`
- `job_trends_db.vw_company_hiring_trends`
- `job_trends_db.vw_location_salary_analysis`
- `job_trends_db.vw_salary_by_seniority`
- `job_trends_db.vw_skills_trend_30days`

The SQL for these views is in [ATHENA_SQL.md](ATHENA_SQL.md).

## Least-Privilege IAM Policy Template

Replace these placeholders before attaching the policy:

- `<REGION>`: `us-east-1`
- `<ACCOUNT_ID>`: your AWS account ID
- `<DATA_BUCKET>`: `job-trends-pipeline-12345`
- `<RESULTS_PREFIX>`: `athena-results/*`
- `<WORKGROUP>`: `primary`
- `<DATABASE>`: `job_trends_db`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AthenaQueryExecution",
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "athena:StopQueryExecution",
        "athena:GetWorkGroup"
      ],
      "Resource": [
        "arn:aws:athena:<REGION>:<ACCOUNT_ID>:workgroup/<WORKGROUP>"
      ]
    },
    {
      "Sid": "GlueCatalogReadOnly",
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetDatabases",
        "glue:GetTable",
        "glue:GetTables",
        "glue:GetPartition",
        "glue:GetPartitions"
      ],
      "Resource": [
        "arn:aws:glue:<REGION>:<ACCOUNT_ID>:catalog",
        "arn:aws:glue:<REGION>:<ACCOUNT_ID>:database/<DATABASE>",
        "arn:aws:glue:<REGION>:<ACCOUNT_ID>:table/<DATABASE>/*"
      ]
    },
    {
      "Sid": "ReadDataLakeObjects",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::<DATA_BUCKET>/processed/*",
        "arn:aws:s3:::<DATA_BUCKET>/curated/*",
        "arn:aws:s3:::<DATA_BUCKET>/raw/*"
      ]
    },
    {
      "Sid": "ListDataLakeBucket",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::<DATA_BUCKET>"
      ]
    },
    {
      "Sid": "AthenaResultsReadWrite",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:AbortMultipartUpload"
      ],
      "Resource": [
        "arn:aws:s3:::<DATA_BUCKET>/<RESULTS_PREFIX>"
      ]
    },
    {
      "Sid": "ListResultsPrefix",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::<DATA_BUCKET>"
      ],
      "Condition": {
        "StringLike": {
          "s3:prefix": [
            "<RESULTS_PREFIX>"
          ]
        }
      }
    }
  ]
}
```
