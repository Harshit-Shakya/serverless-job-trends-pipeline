# Athena SQL

This file contains the Athena database, external table, and view definitions used by the dashboard.

The processed Athena tables are currently non-partitioned. The S3 folders may contain date-shaped paths, but these table definitions do not declare partition columns, so `MSCK REPAIR TABLE` is not required for the current design.

## Database

```sql
CREATE DATABASE IF NOT EXISTS job_trends_db;
```

## External Tables

### Cleaned Jobs

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS job_trends_db.cleaned_jobs (
  job_id STRING,
  job_title STRING,
  job_description STRING,
  company_name STRING,
  location STRING,
  salary_min DOUBLE,
  salary_max DOUBLE,
  salary_avg DOUBLE,
  posted_date TIMESTAMP,
  category STRING,
  source STRING,
  ingestion_date TIMESTAMP
)
STORED AS PARQUET
LOCATION 's3://job-trends-pipeline-12345/processed/cleaned_jobs/';
```

### Skills Fact

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS job_trends_db.skills_fact (
  job_id STRING,
  job_title STRING,
  company_name STRING,
  location STRING,
  salary_avg DOUBLE,
  posted_date TIMESTAMP,
  skill STRING
)
STORED AS PARQUET
LOCATION 's3://job-trends-pipeline-12345/processed/skills_extracted/';
```

## Smoke Test Queries

```sql
SELECT * FROM job_trends_db.cleaned_jobs LIMIT 10;
SELECT * FROM job_trends_db.skills_fact LIMIT 10;
```

## Views

### Top Skills Daily

```sql
CREATE OR REPLACE VIEW job_trends_db.top_skills_daily AS
SELECT 
  skill,
  COUNT(DISTINCT job_id) as job_count,
  AVG(salary_avg) as avg_salary
FROM job_trends_db.skills_fact
WHERE salary_avg IS NOT NULL
GROUP BY skill
ORDER BY job_count DESC;
```

### Salary By Skill

```sql
CREATE OR REPLACE VIEW job_trends_db.salary_by_skill AS
SELECT 
  skill,
  AVG(salary_avg) as avg_salary,
  MIN(salary_avg) as min_salary,
  MAX(salary_avg) as max_salary,
  COUNT(DISTINCT job_id) as sample_size
FROM job_trends_db.skills_fact
WHERE salary_avg > 0
GROUP BY skill
HAVING COUNT(DISTINCT job_id) >= 5
ORDER BY avg_salary DESC;
```

### Skills Trend Over Time

```sql
CREATE OR REPLACE VIEW job_trends_db.vw_skills_trend_30days AS
SELECT
    skill,
    CAST(date(posted_date) AS VARCHAR) AS snapshot_date,
    COUNT(DISTINCT job_id) AS job_count,
    AVG(salary_avg) AS avg_salary
FROM job_trends_db.skills_fact
WHERE salary_avg > 0
  AND posted_date IS NOT NULL
GROUP BY skill, date(posted_date)
ORDER BY snapshot_date, job_count DESC;
```

The dashboard can filter this view to the latest 30 days if required.

### Location Salary Analysis

```sql
CREATE OR REPLACE VIEW job_trends_db.vw_location_salary_analysis AS
SELECT
    location,
    COUNT(DISTINCT job_id) AS total_jobs,
    AVG(salary_avg) AS avg_salary,
    APPROX_PERCENTILE(salary_avg, 0.25) AS p25_salary,
    APPROX_PERCENTILE(salary_avg, 0.75) AS p75_salary
FROM job_trends_db.cleaned_jobs
WHERE salary_avg > 0
  AND location IS NOT NULL
GROUP BY location
ORDER BY avg_salary DESC
LIMIT 20;
```

### Company Hiring Trends

```sql
CREATE OR REPLACE VIEW job_trends_db.vw_company_hiring_trends AS
SELECT
    company_name,
    COUNT(DISTINCT job_id) AS total_openings,
    AVG(salary_avg) AS avg_salary_offered,
    COUNT(DISTINCT category) AS job_categories,
    MAX(posted_date) AS latest_posting_date
FROM job_trends_db.cleaned_jobs
WHERE company_name IS NOT NULL
  AND company_name != ''
GROUP BY company_name
HAVING COUNT(DISTINCT job_id) >= 3
ORDER BY total_openings DESC
LIMIT 50;
```

### Salary By Seniority

```sql
CREATE OR REPLACE VIEW job_trends_db.vw_salary_by_seniority AS
SELECT
    CASE
        WHEN lower(job_title) LIKE '%senior%' OR lower(job_title) LIKE '%sr%' THEN 'Senior'
        WHEN lower(job_title) LIKE '%junior%' OR lower(job_title) LIKE '%jr%' THEN 'Junior'
        WHEN lower(job_title) LIKE '%lead%' OR lower(job_title) LIKE '%principal%' THEN 'Lead'
        WHEN lower(job_title) LIKE '%intern%' OR lower(job_title) LIKE '%entry%' THEN 'Entry-Level'
        ELSE 'Mid-Level'
    END AS seniority_level,
    COUNT(DISTINCT job_id) AS job_count,
    AVG(salary_avg) AS avg_salary,
    APPROX_PERCENTILE(salary_avg, 0.5) AS median_salary,
    MIN(salary_avg) AS min_salary,
    MAX(salary_avg) AS max_salary
FROM job_trends_db.cleaned_jobs
WHERE salary_avg > 0
GROUP BY
    CASE
        WHEN lower(job_title) LIKE '%senior%' OR lower(job_title) LIKE '%sr%' THEN 'Senior'
        WHEN lower(job_title) LIKE '%junior%' OR lower(job_title) LIKE '%jr%' THEN 'Junior'
        WHEN lower(job_title) LIKE '%lead%' OR lower(job_title) LIKE '%principal%' THEN 'Lead'
        WHEN lower(job_title) LIKE '%intern%' OR lower(job_title) LIKE '%entry%' THEN 'Entry-Level'
        ELSE 'Mid-Level'
    END
ORDER BY avg_salary DESC;
```
