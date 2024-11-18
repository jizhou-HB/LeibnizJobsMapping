import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path


def read_jobs_data(csv_file):
    jobs = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Clean and validate lat/lng values
                lat = row["latitude"].strip()
                lng = row["longitude"].strip()

                # Skip jobs with empty coordinates
                if not lat or not lng:
                    continue

                jobs.append(
                    {
                        "city": row["city"],
                        "title": row["title"],
                        "published_date": row["published date"],
                        "url": row["url"],
                        "position": {
                            "lat": float(lat),
                            "lng": float(lng),
                        },
                    }
                )
            except (ValueError, KeyError) as e:
                print(
                    f"Skipping job due to invalid coordinates: {row.get('title', 'Unknown')} - {str(e)}"
                )
                continue
    return jobs


def generate_map_html(jobs, api_key):
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Job Locations Map</title>
        <script src="https://maps.googleapis.com/maps/api/js?key={api_key}"></script>
        <style>
            #map {{ height: 100%; width: 100%; position: absolute; }}
            html, body {{ height: 100%; margin: 0; padding: 0; }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            function initMap() {{
                const jobs = {jobs_json};
                const map = new google.maps.Map(document.getElementById('map'), {{
                    zoom: 6,
                    center: {{ lat: 51.1657, lng: 10.4515 }}, // Center of Germany
                }});

                jobs.forEach(job => {{
                    const marker = new google.maps.Marker({{
                        position: job.position,
                        map: map,
                        title: job.title
                    }});

                    const infowindow = new google.maps.InfoWindow({{
                        content: `<div>
                            <h3>${{job.title}}</h3>
                            <p>City: ${{job.city}}</p>
                            <p>Published: ${{job.published_date}}</p>
                            <a href="${{job.url}}" target="_blank">View Job Details</a>
                        </div>`
                    }});

                    marker.addListener('click', () => {{
                        infowindow.open(map, marker);
                    }});
                }});
            }}
            window.onload = initMap;
        </script>
    </body>
    </html>
    """

    return html_template.format(api_key=api_key, jobs_json=json.dumps(jobs))


def is_map_recent():
    """Check if latest map is less than 24 hours old"""
    if not os.path.exists("latest_job_map.html"):
        return False

    try:
        latest_map = Path("latest_job_map.html").resolve()
        map_time = datetime.fromtimestamp(latest_map.stat().st_mtime)
        return datetime.now() - map_time < timedelta(hours=24)
    except Exception:
        return False


def is_csv_recent():
    """Check if latest job CSV is less than 24 hours old"""
    if not os.path.exists("latest_job.csv"):
        return False

    try:
        csv_file = Path("latest_job.csv").resolve()
        csv_time = datetime.fromtimestamp(csv_file.stat().st_mtime)
        return datetime.now() - csv_time < timedelta(hours=24)
    except Exception:
        return False


def main():
    # Check if we need to update job listings
    if not is_csv_recent():
        print("Job listings are more than 24 hours old.")
        print("Please update job listings by running: python3 ./update_job.py")
        return

    # Check if we have a recent map
    if is_map_recent():
        print("Existing map is less than 24 hours old. Skipping map generation.")
        return

    # Replace with your Google Maps API key
    API_KEY = "AIzaSyC6I2HbXgnDkyBnxluNYloC_lD2N8BcfUw"

    # Read jobs data from latest jobs file
    jobs = read_jobs_data("latest_job.csv")

    # Generate HTML
    html_content = generate_map_html(jobs, API_KEY)

    # Save to file
    output_filename = f'jobs_map_{datetime.now().strftime("%Y%m%d")}.html'
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Create/update symbolic link to latest map
    if os.path.exists("latest_job_map.html"):
        os.remove("latest_job_map.html")
    os.symlink(output_filename, "latest_job_map.html")

    print(f"Map has been generated as {output_filename}")
    print("Symbolic link 'latest_job_map.html' has been updated")


if __name__ == "__main__":
    main()
