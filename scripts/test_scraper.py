#!/usr/bin/env python3
"""
Script to test image scraping for a single pandel.
Usage: python test_scraper.py <pandel_id>
"""

import sys
import requests
import time

API_BASE_URL = "http://localhost:8000"

def test_single_pandel(pandel_id: int):
    """Test image scraping for a single pandel"""
    print(f"Testing image scraping for pandel ID: {pandel_id}")
    
    # First check if pandel exists and get current status
    try:
        status_url = f"{API_BASE_URL}/pandel/{pandel_id}/scrape-status"
        response = requests.get(status_url, timeout=10)
        response.raise_for_status()
        
        status = response.json()
        print(f"Pandel: {status.get('name', 'Unknown')}")
        print(f"Current images: {status.get('total_images', 0)}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error checking pandel status: {str(e)}")
        return
    
    # Trigger scraping
    try:
        scrape_url = f"{API_BASE_URL}/pandel/{pandel_id}/scrape-images"
        params = {"max_images": 3}  # Limit for testing
        
        print("Starting image scraping...")
        response = requests.post(scrape_url, params=params, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        print(f"✓ {result.get('detail', 'Scraping started')}")
        
        # Wait a bit and check status again
        print("Waiting 60 seconds for scraping to complete...")
        time.sleep(60)
        
        # Check final status
        response = requests.get(status_url, timeout=10)
        response.raise_for_status()
        
        final_status = response.json()
        print(f"Final image count: {final_status.get('total_images', 0)}")
        print(f"Images: {final_status.get('images', [])}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error during scraping: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_scraper.py <pandel_id>")
        sys.exit(1)
    
    try:
        pandel_id = int(sys.argv[1])
        test_single_pandel(pandel_id)
    except ValueError:
        print("Error: pandel_id must be a number")
        sys.exit(1)
