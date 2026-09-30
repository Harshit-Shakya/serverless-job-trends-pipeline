import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import *
from datetime import datetime

# Get arguments
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'S3_BUCKET'])

# Initialize Spark & Glue
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# -------------------------------
# 🔹 READ DATA (FIXED)
# -------------------------------
# Read ALL data instead of only today's folder
input_path = f"s3://{args['S3_BUCKET']}/raw/adzuna/"

df = (
    spark.read
    .option("recursiveFileLookup", "true")
    .option("multiline", "true")
    .json(input_path)
)
# -------------------------------
# 🔹 DATA CLEANING
# -------------------------------
cleaned_df = df.select(
    col("id").cast("string").alias("job_id"),
    col("title").alias("job_title"),
    col("description").alias("job_description"),
    col("company.display_name").alias("company_name"),
    col("location.display_name").alias("location"),
    col("salary_min").cast("double"),
    col("salary_max").cast("double"),
    col("created").cast("timestamp").alias("posted_date"),
    col("category.label").alias("category"),
    lit("adzuna").alias("source")
).filter(
    col("title").isNotNull() &
    col("description").isNotNull()
).dropDuplicates(["job_id"])

# -------------------------------
# 🔹 ADD FEATURES
# -------------------------------
cleaned_df = cleaned_df.withColumn(
    "salary_avg",
    (col("salary_min") + col("salary_max")) / 2
).withColumn(
    "ingestion_date",
    current_timestamp()
)

# -------------------------------
# 🔹 WRITE DATA (PARTITIONED)
# -------------------------------
today = datetime.now()

output_path = f"s3://{args['S3_BUCKET']}/processed/cleaned_jobs/{today.year}/{today.month:02d}/{today.day:02d}/"

cleaned_df.write.mode("overwrite").parquet(output_path)

# Commit job
job.commit()