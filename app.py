import os
from typing import Dict

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)

try:
    from pyathena import connect
except ImportError:
    connect = None

try:
    from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
except ImportError:
    ClientError = Exception
    NoCredentialsError = Exception
    PartialCredentialsError = Exception


st.set_page_config(
    page_title="Job Analyzer Dashboard",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .metric-card {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
    }
    </style>
""",
    unsafe_allow_html=True,
)


VIEW_SQL = {
    "salary_by_skill": "SELECT * FROM {database}.salary_by_skill",
    "top_skills_daily": "SELECT * FROM {database}.top_skills_daily",
    "company_hiring_trends": "SELECT * FROM {database}.vw_company_hiring_trends",
    "location_salary_analysis": "SELECT * FROM {database}.vw_location_salary_analysis",
    "salary_by_seniority": "SELECT * FROM {database}.vw_salary_by_seniority",
    "skills_trend_30days": "SELECT * FROM {database}.vw_skills_trend_30days",
}

CSV_FILES = {
    "salary_by_skill": ["salary_by_skill.csv"],
    "top_skills_daily": ["top_skills_daily.csv"],
    "company_hiring_trends": ["vw_company_hiring_trends.csv"],
    "location_salary_analysis": ["vw_location_salary_analysis.csv"],
    "salary_by_seniority": ["vw_salary_by_seniority.csv"],
    "skills_trend_30days": ["vw_skills_trend_30days.csv", "vw_skills_trend.csv"],
}

NUMERIC_COLUMNS = {
    "salary_by_skill": ["avg_salary", "min_salary", "max_salary", "sample_size"],
    "top_skills_daily": ["job_count", "avg_salary"],
    "company_hiring_trends": ["total_openings", "avg_salary_offered", "job_categories"],
    "location_salary_analysis": ["total_jobs", "avg_salary", "p25_salary", "p75_salary"],
    "salary_by_seniority": ["job_count", "avg_salary", "median_salary", "min_salary", "max_salary"],
    "skills_trend_30days": ["job_count", "avg_salary"],
}

DATE_COLUMNS = {
    "company_hiring_trends": ["latest_posting_date"],
    "skills_trend_30days": ["snapshot_date"],
}


def format_plotly_fig(fig):
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="gray"),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig


def get_setting(name: str, default: str = "") -> str:
    env_value = os.getenv(name)
    if env_value is not None and env_value != "":
        return env_value
    if name in st.secrets:
        return str(st.secrets[name])
    return default


def empty_datasets() -> Dict[str, pd.DataFrame]:
    return {key: pd.DataFrame() for key in VIEW_SQL}


def normalize_datasets(datasets: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    for dataset_name, df in datasets.items():
        if df.empty:
            continue
        for col in NUMERIC_COLUMNS.get(dataset_name, []):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        for col in DATE_COLUMNS.get(dataset_name, []):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
    return datasets


def read_csv_candidates(paths):
    last_error = None
    for path in paths:
        try:
            return pd.read_csv(path)
        except FileNotFoundError as exc:
            last_error = exc
            continue
    raise last_error if last_error else FileNotFoundError(f"No CSV found in candidates: {paths}")


@st.cache_data(ttl=int(get_setting("CACHE_TTL_SECONDS", "120")))
def load_data_csv():
    data = {}
    for key, files in CSV_FILES.items():
        data[key] = read_csv_candidates(files)
    return normalize_datasets(data)


@st.cache_data(ttl=int(get_setting("CACHE_TTL_SECONDS", "120")))
def load_data_athena():
    if connect is None:
        raise RuntimeError("`pyathena` is not installed. Install dependencies from requirements.txt.")

    database = get_setting("ATHENA_DATABASE", "job_trends_db")
    region = get_setting("AWS_DEFAULT_REGION", "")
    workgroup = get_setting("ATHENA_WORKGROUP", "primary")
    output_s3 = get_setting("ATHENA_OUTPUT_S3", "")

    if not output_s3:
        raise ValueError("Missing `ATHENA_OUTPUT_S3`. Set it in env vars or Streamlit secrets.")
    if not output_s3.startswith("s3://"):
        raise ValueError("`ATHENA_OUTPUT_S3` must start with `s3://`.")
    if not region:
        raise ValueError("Missing `AWS_DEFAULT_REGION`.")

    conn = connect(
        s3_staging_dir=output_s3,
        region_name=region,
        schema_name=database,
        work_group=workgroup,
    )

    try:
        pd.read_sql("SELECT 1", conn)
        data = {}
        for key, sql in VIEW_SQL.items():
            data[key] = pd.read_sql(sql.format(database=database), conn)
    finally:
        conn.close()

    return normalize_datasets(data)


def safe_values(df: pd.DataFrame, col: str):
    if col not in df.columns:
        return pd.Series(dtype=object)
    return df[col].dropna()


def has_columns(df: pd.DataFrame, cols):
    return all(col in df.columns for col in cols)


def get_data():
    source = get_setting("DATA_SOURCE", "athena").strip().lower()
    try:
        if source == "csv":
            return load_data_csv(), None, source
        return load_data_athena(), None, source
    except ValueError as exc:
        return empty_datasets(), f"Configuration error: {exc}", source
    except (NoCredentialsError, PartialCredentialsError):
        return empty_datasets(), "AWS credentials are missing or incomplete. Check Streamlit secrets.", source
    except ClientError as exc:
        return empty_datasets(), f"AWS error while querying Athena: {exc}", source
    except Exception as exc:
        return empty_datasets(), f"Athena query failure: {exc}", source


st.sidebar.title("💼 Job Analyzer")
st.sidebar.markdown("Explore tech job market trends, salaries, and top employers.")

if st.sidebar.button("Refresh data now"):
    st.cache_data.clear()
    st.rerun()

datasets, load_error, data_source = get_data()
st.sidebar.caption(f"Data source: `{data_source}`")

if load_error:
    st.error(load_error)
    if data_source != "csv":
        st.info("For local demo only, set `DATA_SOURCE=csv` to use exported files.")

df_salary_skill = datasets["salary_by_skill"]
df_top_skills = datasets["top_skills_daily"]
df_company_trends = datasets["company_hiring_trends"]
df_location_salary = datasets["location_salary_analysis"]
df_seniority = datasets["salary_by_seniority"]
df_skills_trend = datasets["skills_trend_30days"]

if all(df.empty for df in datasets.values()):
    st.warning("All datasets are empty. This can happen if queries return no rows or access is misconfigured.")

all_skills = (
    set(safe_values(df_salary_skill, "skill"))
    | set(safe_values(df_top_skills, "skill"))
    | set(safe_values(df_skills_trend, "skill"))
)

selected_skills = st.sidebar.multiselect(
    "Filter by Skill(s):",
    options=sorted(list(all_skills)),
    default=[],
)

if selected_skills:
    df_salary_skill_f = df_salary_skill[df_salary_skill["skill"].isin(selected_skills)] if "skill" in df_salary_skill.columns else df_salary_skill
    df_top_skills_f = df_top_skills[df_top_skills["skill"].isin(selected_skills)] if "skill" in df_top_skills.columns else df_top_skills
    df_skills_trend_f = df_skills_trend[df_skills_trend["skill"].isin(selected_skills)] if "skill" in df_skills_trend.columns else df_skills_trend
else:
    df_salary_skill_f = df_salary_skill.copy()
    df_top_skills_f = df_top_skills.copy()
    df_skills_trend_f = df_skills_trend.copy()

st.title("Tech Job Market Analytics")

tab1, tab2, tab3 = st.tabs(["📊 Skills & Trends", "🏢 Geography & Employers", "📈 Career Pathways"])

with tab1:
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    total_unique_skills = df_top_skills_f["skill"].nunique() if "skill" in df_top_skills_f.columns else 0

    if has_columns(df_top_skills_f, ["skill", "job_count", "avg_salary"]) and not df_top_skills_f.empty:
        top_skill = df_top_skills_f.sort_values(by="job_count", ascending=False).iloc[0]["skill"]
        highest_paying = df_top_skills_f.sort_values(by="avg_salary", ascending=False).iloc[0]["skill"]
        overall_avg_salary = df_top_skills_f["avg_salary"].mean()
    else:
        top_skill, highest_paying, overall_avg_salary = "N/A", "N/A", 0

    kpi1.metric("Total Unique Skills", f"{total_unique_skills}")
    kpi2.metric("Top Skill by Demand", f"{top_skill}")
    kpi3.metric("Highest Paying Skill", f"{highest_paying}")
    kpi4.metric("Overall Avg Salary", f"£{overall_avg_salary:,.0f}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top Skills by Demand")
        if has_columns(df_top_skills_f, ["skill", "job_count", "avg_salary"]) and not df_top_skills_f.empty:
            fig_bar = px.bar(
                df_top_skills_f.sort_values(by="job_count", ascending=True).tail(15),
                x="job_count",
                y="skill",
                orientation="h",
                color="avg_salary",
                color_continuous_scale="Blues",
                labels={"job_count": "Job Count", "skill": "Skill", "avg_salary": "Avg Salary"},
            )
            fig_bar.update_layout(coloraxis_colorbar=dict(title="Salary (£)"))
            st.plotly_chart(format_plotly_fig(fig_bar), use_container_width=True)
        else:
            st.info("No data available for this chart.")

    with col2:
        st.subheader("Demand vs Salary Matrix")
        if has_columns(df_salary_skill_f, ["sample_size", "avg_salary", "skill"]) and not df_salary_skill_f.empty:
            fig_scatter = px.scatter(
                df_salary_skill_f,
                x="sample_size",
                y="avg_salary",
                size="sample_size",
                hover_name="skill",
                color="avg_salary",
                color_continuous_scale="Tealrose",
                labels={"sample_size": "Sample Size (Demand)", "avg_salary": "Average Salary (£)"},
            )
            median_x = df_salary_skill_f["sample_size"].median()
            median_y = df_salary_skill_f["avg_salary"].median()
            fig_scatter.add_vline(x=median_x, line_dash="dash", line_color="gray", opacity=0.7)
            fig_scatter.add_hline(y=median_y, line_dash="dash", line_color="gray", opacity=0.7)

            st.plotly_chart(format_plotly_fig(fig_scatter), use_container_width=True)
        else:
            st.info("No data available for this chart.")

    st.subheader("Skills Demand Over Time")
    if has_columns(df_skills_trend_f, ["snapshot_date", "job_count", "skill"]) and not df_skills_trend_f.empty:
        fig_line = px.line(
            df_skills_trend_f.sort_values("snapshot_date"),
            x="snapshot_date",
            y="job_count",
            color="skill",
            markers=True,
            labels={"snapshot_date": "Date", "job_count": "Job Postings", "skill": "Skill"},
        )
        st.plotly_chart(format_plotly_fig(fig_line), use_container_width=True)
    else:
        st.info("No data available for this chart.")

with tab2:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Company Hiring Trends (Treemap)")

        if has_columns(df_company_trends, ["company_name", "total_openings", "avg_salary_offered"]) and not df_company_trends.empty:
            df_comp = df_company_trends.dropna(subset=["company_name", "total_openings"]).copy()
            df_comp["total_openings"] = pd.to_numeric(df_comp["total_openings"], errors="coerce")
            df_comp = df_comp.nlargest(30, "total_openings")
            df_comp["Root"] = "Companies"

            fig_tree = px.treemap(
                df_comp,
                path=["Root", "company_name"],
                values="total_openings",
                color="avg_salary_offered",
                color_continuous_scale="Blues",
                labels={"total_openings": "Total Openings", "avg_salary_offered": "Avg Salary"},
            )
            st.plotly_chart(format_plotly_fig(fig_tree), use_container_width=True)
        else:
            st.info("No data available for this chart.")

    with col2:
        st.subheader("Top Locations by Total Jobs")
        if has_columns(df_location_salary, ["location", "total_jobs", "avg_salary"]) and not df_location_salary.empty:
            df_loc_bar = (
                df_location_salary.dropna(subset=["location", "total_jobs"])
                .nlargest(15, "total_jobs")
                .sort_values("total_jobs", ascending=True)
            )
            fig_loc_bar = px.bar(
                df_loc_bar,
                x="total_jobs",
                y="location",
                orientation="h",
                color="avg_salary",
                color_continuous_scale="Tealrose",
                labels={"total_jobs": "Total Jobs", "location": "Location", "avg_salary": "Avg Salary"},
            )
            st.plotly_chart(format_plotly_fig(fig_loc_bar), use_container_width=True)
        else:
            st.info("No data available for this chart.")

    st.markdown("---")
    st.subheader("Salary Spread by City")

    if has_columns(df_location_salary, ["location", "p25_salary", "p75_salary", "avg_salary", "total_jobs"]) and not df_location_salary.empty:
        df_loc = df_location_salary.dropna(subset=["location", "p25_salary", "p75_salary", "avg_salary"]).copy()

        for col in ["p25_salary", "p75_salary", "avg_salary", "total_jobs"]:
            df_loc[col] = pd.to_numeric(df_loc[col], errors="coerce")

        df_loc = df_loc.dropna(subset=["p25_salary", "p75_salary", "avg_salary"]).nlargest(20, "total_jobs")

        fig_range = go.Figure()

        fig_range.add_trace(
            go.Bar(
                x=df_loc["location"],
                y=df_loc["p75_salary"] - df_loc["p25_salary"],
                base=df_loc["p25_salary"],
                name="Salary Range (25th - 75th %)",
                marker_color="rgba(55, 128, 191, 0.6)",
                hoverinfo="x+y+text",
                text=[f"P25: £{p25:,.0f} | P75: £{p75:,.0f}" for p25, p75 in zip(df_loc["p25_salary"], df_loc["p75_salary"])],
            )
        )

        fig_range.add_trace(
            go.Scatter(
                x=df_loc["location"],
                y=df_loc["avg_salary"],
                mode="markers",
                name="Average Salary",
                marker=dict(color="white", size=8, line=dict(color="red", width=2)),
            )
        )

        fig_range.update_layout(barmode="overlay", yaxis_title="Salary (£)")
        st.plotly_chart(format_plotly_fig(fig_range), use_container_width=True)
    else:
        st.info("No data available for this chart.")

with tab3:
    st.subheader("Salary by Seniority Level")

    if has_columns(df_seniority, ["seniority_level", "avg_salary", "max_salary", "min_salary"]) and not df_seniority.empty:
        seniority_order = ["Entry-Level", "Junior", "Mid-Level", "Senior", "Lead"]
        df_sen = df_seniority.copy()
        df_sen["seniority_level"] = pd.Categorical(df_sen["seniority_level"], categories=seniority_order, ordered=True)
        df_sen = df_sen.sort_values("seniority_level")

        fig_seniority = go.Figure()

        fig_seniority.add_trace(
            go.Bar(
                x=df_sen["seniority_level"],
                y=df_sen["avg_salary"],
                error_y=dict(
                    type="data",
                    symmetric=False,
                    array=df_sen["max_salary"] - df_sen["avg_salary"],
                    arrayminus=df_sen["avg_salary"] - df_sen["min_salary"],
                    color="gray",
                    thickness=1.5,
                ),
                marker_color="#1E88E5",
                text=[f"Avg: £{avg:,.0f}" for avg in df_sen["avg_salary"]],
                textposition="auto",
            )
        )

        fig_seniority.update_layout(yaxis_title="Salary (£)")
        st.plotly_chart(format_plotly_fig(fig_seniority), use_container_width=True)
    else:
        st.info("No data available for this chart.")

    st.markdown("---")

    st.subheader("Master Data Table: Salary by Skill")
    if not df_salary_skill_f.empty and has_columns(df_salary_skill_f, ["avg_salary", "min_salary", "max_salary"]):
        display_df = df_salary_skill_f.copy()
        for col in ["avg_salary", "min_salary", "max_salary"]:
            display_df[col] = display_df[col].apply(lambda x: f"£{x:,.2f}" if pd.notnull(x) else "N/A")

        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "skill": "Skill",
                "avg_salary": "Average Salary",
                "min_salary": "Minimum Salary",
                "max_salary": "Maximum Salary",
                "sample_size": "Sample Size",
            },
        )
    else:
        st.info("No data available for this table.")
