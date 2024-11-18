import subprocess

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from jobs_map import is_csv_recent, read_jobs_data


def refresh_jobs():
    try:
        subprocess.run(["python3", "./update_job.py"], check=True)
        st.success("Job listings successfully updated!")
        st.rerun()
    except subprocess.CalledProcessError:
        st.error("Failed to update job listings")


def main():
    st.set_page_config(page_title="Job Locations Map", layout="wide")
    st.title("Job Locations Map")

    # Add refresh button
    if st.button("Refresh Job Listings"):
        refresh_jobs()

    if not is_csv_recent():
        st.error(
            "Job listings are more than 24 hours old. Please update job listings by running: python3 ./update_job.py"
        )
        return

    # Read jobs data
    jobs = read_jobs_data("latest_job.csv")

    if not jobs:
        st.error("No job data available")
        return

    # Add filters in sidebar
    st.sidebar.header("Filters")

    # Date filter
    min_date = pd.to_datetime([job["published_date"] for job in jobs]).min()
    max_date = pd.to_datetime([job["published_date"] for job in jobs]).max()

    selected_date = st.sidebar.date_input(
        "Select Date",
        value=min_date,
        min_value=min_date,
        max_value=pd.to_datetime("today").date(),
    )

    # Convert jobs to DataFrame for mapping
    df = pd.DataFrame(
        [
            {
                "lat": job["position"]["lat"],
                "lon": job["position"]["lng"],
                "title": job["title"],
                "city": job["city"],
                "published_date": job["published_date"],
                "url": job["url"],
            }
            for job in jobs
        ]
    )

    # Apply filters
    df["published_date"] = pd.to_datetime(df["published_date"])
    mask = df["published_date"].dt.date >= selected_date
    df = df[mask]

    # Filter jobs list to match DataFrame
    jobs = [
        job
        for job in jobs
        if pd.to_datetime(job["published_date"]).date() >= selected_date
    ]

    if len(jobs) == 0:
        st.warning("No jobs match the selected filters")
        return

    # Display the map
    col1, col2 = st.columns([2, 1])

    with col1:
        # Create a folium map centered on the mean position of all jobs
        m = folium.Map(location=[df["lat"].mean(), df["lon"].mean()], zoom_start=4)

        # Add markers for each job
        for idx, job in enumerate(jobs):
            html = f"""
                <div style="min-width: 200px;">
                    <b>{job['title']}</b><br>
                    Location: {job['city']}<br>
                    Published: {job['published_date']}<br>
                    <a href="{job['url']}" target="_blank">View Job Details</a>
                </div>
            """

            folium.Marker(
                location=[job["position"]["lat"], job["position"]["lng"]],
                popup=html,
                tooltip=f"{job['title']} - {job['city']}",
                id=f"marker_{idx}",
            ).add_to(m)

        # Display the map
        map_data = st_folium(m, width=800, height=600)

        # Handle marker clicks
        if map_data["last_clicked"]:
            clicked_lat = map_data["last_clicked"]["lat"]
            clicked_lng = map_data["last_clicked"]["lng"]
            # Find the corresponding job
            for idx, job in enumerate(jobs):
                if (
                    abs(job["position"]["lat"] - clicked_lat) < 0.0001
                    and abs(job["position"]["lng"] - clicked_lng) < 0.0001
                ):
                    st.session_state.selected_job = idx

    with col2:
        st.subheader("Job Listings")
        for idx, job in enumerate(jobs):
            with st.expander(
                f"{job['title']} - {job['city']}",
                expanded=st.session_state.get("selected_job") == idx,
            ):
                st.write(f"Published: {job['published_date']}")
                st.markdown(f"[View Job Details]({job['url']})")


if __name__ == "__main__":
    main()
