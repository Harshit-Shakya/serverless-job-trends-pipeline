# Pre-Push Checklist

Use this checklist before publishing the repository to GitHub.

## Secret Safety

- Confirm `.env` is ignored by Git.
- Confirm `.streamlit/secrets.toml` is ignored by Git.
- Confirm no real AWS keys are committed.
- Confirm no Adzuna API credentials are committed.
- Confirm `Scripts Used in AWS/lambda Function script/lambda_function.py` contains environment variable names only, not real secrets.
- If real credentials were ever pushed, pasted publicly, or exposed in screenshots, rotate them in AWS IAM and Adzuna before publishing.

Search for likely secrets:

```powershell
rg -n "AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|ADZUNA_APP_KEY|ADZUNA_APP_ID|AKIA|SECRET|app_key" -S
```

The search may find safe placeholder names or environment variable references. It should not find real credential values.

## Git Ignore Check

These should not be committed:

- `.env`
- `.venv/`
- `.tmp/`
- `__pycache__/`
- `.pytest_cache/`
- `.streamlit/secrets.toml`
- `*.pyc`
- local logs

After initializing Git, check:

```powershell
git status --short
```

If ignored files still appear, fix `.gitignore` before committing.

## Syntax Checks

Run:

```powershell
python -m py_compile app.py
python -m py_compile "Scripts Used in AWS/lambda Function script/lambda_function.py"
```

Do not compile or run the Glue scripts locally unless the AWS Glue/Spark runtime is available.

## Dashboard Checks

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run Streamlit:

```powershell
streamlit run app.py
```

Test local demo mode:

```text
DATA_SOURCE=csv
```

Test live Athena mode:

```text
DATA_SOURCE=athena
```

## AWS Cost Control

Before interviews, demos, or idle periods:

- Disable EventBridge schedules if daily ingestion is not needed.
- Disable or pause Glue workflow triggers if ETL is not needed.
- Stop any active Glue job, workflow, or crawler run.
- Keep S3, Athena, Glue jobs, IAM roles, Lambda code, and dashboard code intact.

This preserves the project while preventing unnecessary AWS usage.

## Final README Review

Before the first public push, verify:

- `README.md` explains the architecture clearly.
- `ATHENA_SQL.md` contains the table and view SQL.
- `STREAMLIT_SETUP.md` uses `us-east-1`.
- `AWS_CONSOLE_SETUP.md` matches the real AWS resources.
- Screenshots do not reveal account IDs, access keys, secret keys, or private billing details.
