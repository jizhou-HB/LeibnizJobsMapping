#!/usr/bin/env python3
import os
from datetime import datetime

import pandas as pd

from get_job_info import add_geolocation, process_address_data, retrieve_job_listings


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


def main():
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


if __name__ == "__main__":
    main()
