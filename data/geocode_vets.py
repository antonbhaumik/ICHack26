#!/usr/bin/env python3
"""
Script to pre-compute geocoding for all vet addresses in vets_data.csv
This creates a new file vets_data_geocoded.csv with latitude and longitude columns
"""

import csv
import os
import time
from requests import get
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY not found in environment variables")
    exit(1)

def geocode_address(address):
    """Geocode an address using Google Maps API"""
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": address, "key": GOOGLE_API_KEY}
        r = get(url, params=params)
        r.raise_for_status()
        data = r.json()
        
        if data["status"] == "OK" and data["results"]:
            location = data["results"][0]["geometry"]["location"]
            return location['lat'], location['lng']
        else:
            print(f"  Warning: Could not geocode address (status: {data.get('status', 'unknown')})")
            return None, None
    except Exception as e:
        print(f"  Error: {e}")
        return None, None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, 'vets_data.csv')
    output_file = os.path.join(script_dir, 'vets_data_geocoded.csv')
    
    print(f"Reading vets from: {input_file}")
    print(f"Output will be saved to: {output_file}")
    print()
    
    vets_geocoded = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        vets = list(reader)
    
    print(f"Found {len(vets)} vets to geocode")
    print("Starting geocoding...")
    print()
    
    for i, vet in enumerate(vets, 1):
        name = vet['Hospital Name']
        address = vet['Address']
        
        print(f"[{i}/{len(vets)}] Geocoding: {name}")
        
        lat, lng = geocode_address(address)
        
        vets_geocoded.append({
            'Hospital Name': name,
            'Address': address,
            'Latitude': lat if lat is not None else '',
            'Longitude': lng if lng is not None else ''
        })
        
        if lat and lng:
            print(f"  ✓ Success: {lat:.6f}, {lng:.6f}")
        else:
            print(f"  ✗ Failed to geocode")
        
        # Small delay to avoid rate limiting
        time.sleep(0.1)
    
    # Write to output file
    print()
    print(f"Writing results to: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['Hospital Name', 'Address', 'Latitude', 'Longitude']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(vets_geocoded)
    
    success_count = sum(1 for v in vets_geocoded if v['Latitude'] and v['Longitude'])
    print(f"✓ Done! Successfully geocoded {success_count}/{len(vets)} vets")
    print(f"Results saved to: {output_file}")

if __name__ == '__main__':
    main()
