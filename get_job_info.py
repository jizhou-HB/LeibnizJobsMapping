import random

import pandas as pd
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
