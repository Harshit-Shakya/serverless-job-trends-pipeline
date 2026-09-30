import json
import boto3
import requests
from datetime import datetime
import os

s3 = boto3.client('s3')

BUCKET_NAME = os.environ['S3_BUCKET']
ADZUNA_APP_ID = os.environ['ADZUNA_APP_ID']
ADZUNA_APP_KEY = os.environ['ADZUNA_APP_KEY']


def lambda_handler(event, context):
    """
    Fetch job postings from Adzuna API and store in S3
    """

    # API endpoint (use GB - stable)
    url = "https://api.adzuna.com/v1/api/jobs/gb/search/1"

    # Clean & valid parameters
    params = {
        'app_id': ADZUNA_APP_ID,
        'app_key': ADZUNA_APP_KEY,
        'results_per_page': 50,
        'what': 'software engineer'
    }

    headers = {
        "Accept": "application/json"
    }

    all_jobs = []

    for page in range(1, 3):
        url = f"https://api.adzuna.com/v1/api/jobs/gb/search/{page}"

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        print(f"Page {page} STATUS:", response.status_code)

        if response.status_code == 200:
            data = response.json()
            all_jobs.extend(data.get('results', []))
        else:
            print(f"Error fetching page {page}: {response.status_code}")
            print("Response:", response.text[:300])

    # Save to S3 with partitioned path
    today = datetime.now()
    s3_key = f"raw/adzuna/{today.year}/{today.month:02d}/{today.day:02d}/jobs_{today.strftime('%Y%m%d_%H%M%S')}.json"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=json.dumps(all_jobs, indent=2),
        ContentType='application/json'
    )

    return {
        'statusCode': 200,
        'body': json.dumps(f"Fetched {len(all_jobs)} jobs to {s3_key}")
    }
