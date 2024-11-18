# Job Listings Scraper

A Python script for scraping and processing job listings from Leibniz Psychology's job board (https://leibniz-psychology.org/jobboerse). The script retrieves job listings, processes location data, and adds geolocation coordinates for mapping purposes.

## Features

- Scrapes job listings from Leibniz Psychology's job board
- Extracts city, job title, publication date, and URL information
- Adds geolocation data (latitude/longitude) for each job location
- Implements caching for German city coordinates to minimize API calls
- Adds small random offsets to coordinates to prevent marker overlap on maps

## Requirements

```
pandas
requests
beautifulsoup4
geopy
```

## Usage

```python
from get_job_info import retrieve_job_listings, process_address_data, add_geolocation

# Get job listings
job_listings = retrieve_job_listings()

# Process into structured data
job_data = process_address_data(job_listings)

# Add geolocation data
job_data_with_coords = add_geolocation(job_data)
```

## Functions

### retrieve_job_listings()
Scrapes the job board and returns a list of job listings containing address, URL, and publication date.

### process_address_data()
Converts raw job listing data into a structured pandas DataFrame with columns:
- city
- title
- published date
- url

### add_geolocation()
Adds latitude and longitude coordinates for each job location using:
- Cached coordinates for German cities
- Nominatim geocoding service for new cities
- Small random offset to prevent marker overlap

## Note

The script includes a caching mechanism for city coordinates to minimize API calls to the geocoding service. The cache is automatically maintained in a separate file.
