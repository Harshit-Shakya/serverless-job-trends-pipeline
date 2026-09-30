import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import *
from pyspark.sql.types import *
import re

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'S3_BUCKET'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# -------------------------------
# SKILLS LIST
# -------------------------------
SKILLS = [
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust", "Ruby", "PHP",
    "React", "Angular", "Vue", "Node.js", "Django", "Flask", "Spring", "Express",
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Jenkins", "Git", "CI/CD",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Scikit-learn",
    "Agile", "Scrum", "REST API", "GraphQL", "Microservices"
]

# -------------------------------
# UDF FOR SKILL EXTRACTION
# -------------------------------
def extract_skills(text):
    if not text:
        return []
    
    found_skills = []
    for skill in SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            found_skills.append(skill)
    
    return found_skills

extract_skills_udf = udf(extract_skills, ArrayType(StringType()))

# -------------------------------
# READ CLEANED DATA (IMPORTANT FIX)
# -------------------------------
input_path = f"s3://{args['S3_BUCKET']}/processed/cleaned_jobs/"

df = (
    spark.read
    .option("recursiveFileLookup", "true")
    .parquet(input_path)
)

# -------------------------------
# SKILL EXTRACTION
# -------------------------------
df_with_skills = df.withColumn(
    "text_combined",
    concat_ws(" ", col("job_title"), col("job_description"))
).withColumn(
    "skills",
    extract_skills_udf(col("text_combined"))
)

# -------------------------------
# EXPLODE SKILLS
# -------------------------------
skills_exploded = df_with_skills.select(
    col("job_id"),
    col("job_title"),
    col("company_name"),
    col("location"),
    col("salary_avg"),
    col("posted_date"),
    explode(col("skills")).alias("skill")
)

# -------------------------------
# WRITE OUTPUT
# -------------------------------
output_path = f"s3://{args['S3_BUCKET']}/processed/skills_extracted/"

skills_exploded.write.mode("overwrite").parquet(output_path)

job.commit()