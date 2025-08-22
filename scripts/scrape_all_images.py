#!/usr/bin/env python3
"""
Script to run image scraping for all existing pandels using API calls.
This script will call the scraping API for each pandel that exists in the database.
"""

import requests
import time
import sys

# Configuration
API_BASE_URL = "http://localhost:8000"  # Update this if your API runs on different host/port
MAX_IMAGES_PER_PANDEL = 7
DELAY_BETWEEN_REQUESTS = 5  # seconds

def get_all_pandel_ids():
    """Fetch all pandel IDs using the API"""
    try:
        url = f"{API_BASE_URL}/pandel/"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        pandels = response.json()
        pandel_ids = []
        for pandel in pandels:
            pandel_id = pandel.get("id")
            if pandel_id:
                pandel_ids.append(int(pandel_id))
        return sorted(pandel_ids)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching pandel IDs from API: {str(e)}")
        return []
    except Exception as e:
        print(f"Error processing pandel data: {str(e)}")
        return []

def trigger_image_scraping(pandel_id: int, max_images: int = MAX_IMAGES_PER_PANDEL):
    """Trigger image scraping for a specific pandel"""
    try:
        url = f"{API_BASE_URL}/pandel/{pandel_id}/scrape-images"
        params = {"max_images": max_images}
        
        response = requests.post(url, params=params, timeout=60)
        response.raise_for_status()
        
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error triggering scraping for pandel {pandel_id}: {str(e)}")
        return None

def check_scrape_status(pandel_id: int):
    """Check the current status/images count for a pandel"""
    try:
        url = f"{API_BASE_URL}/pandel/{pandel_id}/scrape-status"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error checking status for pandel {pandel_id}: {str(e)}")
        return None

def main():
    print("Starting image scraping for all pandels...")
    
    # Get all pandel IDs
    pandel_ids = get_all_pandel_ids()
    
    if not pandel_ids:
        print("No pandels found in database.")
        return
    
    print(f"Found {len(pandel_ids)} pandels to process")
    
    # Process each pandel
    for i, pandel_id in enumerate(pandel_ids, 1):
        print(f"\n[{i}/{len(pandel_ids)}] Processing pandel ID: {pandel_id}")
        
        # Check current status
        status = check_scrape_status(pandel_id)
        if status:
            current_images = status.get("total_images", 0)
            pandel_name = status.get("name", "Unknown")
            print(f"  Pandel: {pandel_name}")
            print(f"  Current images: {current_images}")
            
            # Skip if already has enough images
            if current_images >= MAX_IMAGES_PER_PANDEL:
                print(f"  Skipping - already has {current_images} images")
                continue
        
        # Trigger scraping
        result = trigger_image_scraping(pandel_id, MAX_IMAGES_PER_PANDEL)
        if result:
            print(f"  ✓ Scraping started: {result.get('detail', 'Success')}")
        else:
            print(f"  ✗ Failed to start scraping")
        
        # Wait between requests to avoid overwhelming the server
        if i < len(pandel_ids):  # Don't wait after the last request
            print(f"  Waiting {DELAY_BETWEEN_REQUESTS} seconds...")
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    print(f"\n✓ Completed processing all {len(pandel_ids)} pandels")
    print("Note: Image scraping runs in the background. Check individual pandel status to see progress.")

def check_all_status():
    """Check the current image status for all pandels"""
    print("Checking image status for all pandels...")
    
    pandel_ids = get_all_pandel_ids()
    if not pandel_ids:
        print("No pandels found via API.")
        return
    
    total_pandels = len(pandel_ids)
    pandels_with_images = 0
    total_images = 0
    
    for pandel_id in pandel_ids:
        status = check_scrape_status(pandel_id)
        if status:
            image_count = status.get("total_images", 0)
            pandel_name = status.get("name", "Unknown")
            
            if image_count > 0:
                pandels_with_images += 1
                total_images += image_count
                print(f"  {pandel_name} (ID: {pandel_id}): {image_count} images")
    
    print(f"\nSummary:")
    print(f"  Total pandels: {total_pandels}")
    print(f"  Pandels with images: {pandels_with_images}")
    print(f"  Total images: {total_images}")
    print(f"  Average images per pandel: {total_images/total_pandels if total_pandels > 0 else 0:.1f}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        check_all_status()
    else:
        main()
