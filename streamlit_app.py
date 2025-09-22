fimport folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from jobs_map import is_csv_recent, read_jobs_data

import os
from datetime import datetime
#import pandas as pd
# from get_job_info import add_geolocation, process_address_data, retrieve_job_listings
import random
#import pandas as pd
import requests
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim



def retrieve_job_listings(url="https://leibniz-psychology.org/jobboerse"):
    """
    Retrieve job listings from the specified URL
    Returns a list of job listings or empty list if none found
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        url_prefix = "https://leibniz-psychology.org"
        addresses = []

        for item in soup.find_all("div", class_="article articletype-0"):
            try:
                address = item.find("a", itemprop="url").get("title")
                url = url_prefix + item.find("a", itemprop="url").get("href")
                date = item.find("time", itemprop="datePublished").get("datetime")
                addresses.append(
                    {"address": address, "url": url, "published_date": date}
                )
            except (AttributeError, TypeError):
                continue

        return addresses
    except requests.RequestException as e:
        print(f"Error retrieving job listings: {e}")
        return []


def process_address_data(addresses):
    """
    Process the raw address data into a structured DataFrame
    Returns DataFrame with columns: city, title, published date, url
    """
    if not addresses:
        return pd.DataFrame(columns=["city", "title", "published date", "url"])

    address_book = pd.DataFrame(addresses)
    address_book.columns = ["address", "url", "published date"]

    address_book["city"] = address_book["address"].str.split(":").str[0]
    address_book["title"] = (
        address_book["address"].str.split(":", n=1).str[1].str.strip()
    )

    return address_book[["city", "title", "published date", "url"]]


def add_geolocation(address_book, user_agent="city_to_coordinates"):
    """
    Add geolocation data to the address book using cached German city coordinates
    """
    from germany_cities_cache import load_cache, save_cache

    # Load existing cache
    coordinates_cache = load_cache()
    geolocator = Nominatim(user_agent=user_agent)
    coordinates = []
    cache_updated = False

    for city in address_book["city"]:
        if city in coordinates_cache:
            # Use cached coordinates with small random offset
            base_lat, base_lon = coordinates_cache[city]
            lat = base_lat + random.uniform(-0.02, 0.02)
            lon = base_lon + random.uniform(-0.02, 0.02)
            coordinates.append((lat, lon))
        else:
            # Lookup new city
            location = geolocator.geocode(city)
            if location:
                # Cache the base coordinates
                coordinates_cache[city] = (location.latitude, location.longitude)
                cache_updated = True
                # Add random offset for display
                lat = location.latitude + random.uniform(-0.02, 0.02)
                lon = location.longitude + random.uniform(-0.02, 0.02)
                coordinates.append((lat, lon))
            else:
                coordinates.append(None)

    # Save updated cache if new cities were added
    if cache_updated:
        save_cache(coordinates_cache)

    address_book["latitude"] = [coord[0] if coord else None for coord in coordinates]
    address_book["longitude"] = [coord[1] if coord else None for coord in coordinates]

    return address_book


def save_to_csv(address_book, filename):
    """
    Save address book data to a CSV file and create/update symbolic link
    """
    if not address_book.empty:
        address_book.to_csv(filename, index=False)
        # Create/update symbolic link to latest file
        symlink_name = "latest_job.csv"
        if os.path.exists(symlink_name):
            os.remove(symlink_name)
        os.symlink(filename, symlink_name)


def update_jobs():
    """
    Main function to orchestrate the job listing retrieval and processing
    """
    # Retrieve job listings
    addresses = retrieve_job_listings()

    # Process address data
    address_book = process_address_data(addresses)

    # Add geolocation data
    address_book = add_geolocation(address_book)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"job_listings_{timestamp}.csv"

    # Save to CSV
    save_to_csv(address_book, filename)
    print(f"results are written to {filename}")



def refresh_jobs():
    try:
        update_jobs()
        st.success("Job listings successfully updated!")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to update job listings: {str(e)}")


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
        "Select range: including posts from which day to today?",
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
