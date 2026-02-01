import csv
import os
import re
import unicodedata
from datetime import datetime

from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, session
from flask.cli import load_dotenv
from requests import get
from urllib.parse import urlparse, parse_qs, unquote

# Import the wait time predictor
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data'))
from data.ae_wait_predictor import run_all

app = Flask(__name__)
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

def normalize_hospital_name(name):
    """
    Normalize hospital name for fuzzy matching:
    - Convert to lowercase
    - Remove non-ASCII characters
    - Sort words alphabetically
    - Remove common words that don't help matching
    """
    if not name:
        return ""
    
    # Convert to lowercase
    name = name.lower()
    
    # Remove non-ASCII characters
    name = unicodedata.normalize('NFKD', name)
    name = name.encode('ascii', 'ignore').decode('ascii')
    
    # Remove punctuation and extra whitespace
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Split into words and sort
    words = name.split()
    
    # Remove common words that don't help with matching
    common_words = {'the', 'a', 'an', 'and', 'or', 'of', 'at', 'in', 'for', 'to'}
    words = [w for w in words if w not in common_words]
    
    # Sort words to ignore order
    words.sort()
    
    return ' '.join(words)

def find_hospital_in_data(hospital_name, hospital_df):
    """
    Find a hospital in the dataframe using fuzzy name matching.
    Returns the matched hospital name from the dataframe or None.
    """
    normalized_input = normalize_hospital_name(hospital_name)
    
    # Try exact normalized match first
    for idx, row in hospital_df.iterrows():
        normalized_row_name = normalize_hospital_name(row['hospital_name'])
        if normalized_row_name == normalized_input:
            return row['hospital_name']
    
    # Try partial match - check if all words from input appear in hospital name
    input_words = set(normalized_input.split())
    best_match = None
    best_score = 0
    
    for idx, row in hospital_df.iterrows():
        normalized_row_name = normalize_hospital_name(row['hospital_name'])
        row_words = set(normalized_row_name.split())
        
        # Calculate how many input words are in the row
        matching_words = input_words.intersection(row_words)
        if len(matching_words) > 0:
            score = len(matching_words) / len(input_words)
            if score > best_score:
                best_score = score
                best_match = row['hospital_name']
    
    # Only return match if at least 50% of words matched
    if best_score >= 0.5:
        return best_match
    
    return None

@app.route('/')
def home():
    return render_template('index.html', api_key=GOOGLE_API_KEY)

@app.route('/map')
def map_view():
    place = request.args.get('place', '')
    service_type = session.get('service_type', 'hospital')
    return render_template('map.html', api_key=GOOGLE_API_KEY, place=place, service_type=service_type)


@app.route('/api/get-location', methods=['POST'])
def get_location():
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if latitude and longitude:
        return jsonify({
            'status': 'success',
            'location': {
                'latitude': latitude,
                'longitude': longitude
            }
        })
    return jsonify({'status': 'error', 'message': 'Location not provided'}), 400

def get_all_hospitals(latitude, longitude):
    html = get(
        f"https://www.nhs.uk/service-search/find-an-accident-and-emergency-service/results/your%20location?latitude={latitude}&longitude={longitude}&SelectedFilter=AAndEOpenNow").text

    soup = BeautifulSoup(html, "html.parser")

    results = []

    for item in soup.select("li.results__item"):
        name_el = item.select_one("h3.results__name")
        map_el = item.select_one("a.maplink")

        if not name_el or not map_el:
            continue

        name = name_el.get_text(strip=True)
        url = map_el["href"]

        qs = parse_qs(urlparse(url).query)

        destination = unquote(qs.get("destination", [""])[0])

        results.append({
            "hospital": name,
            "address": destination
        })

    return results

def get_all_vets():
    """Load all vets from the geocoded CSV file"""
    vets = []
    # Try geocoded file first, fall back to regular file
    geocoded_path = os.path.join(os.path.dirname(__file__), 'data', 'vets_data_geocoded.csv')
    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'vets_data.csv')
    
    # Use geocoded file if it exists
    file_to_use = geocoded_path if os.path.exists(geocoded_path) else csv_path
    has_coords = os.path.exists(geocoded_path)
    
    try:
        with open(file_to_use, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                vet_data = {
                    'hospital': row['Hospital Name'],
                    'address': row['Address']
                }
                # Add coordinates if available
                if has_coords and row.get('Latitude') and row.get('Longitude'):
                    try:
                        vet_data['lat'] = float(row['Latitude'])
                        vet_data['lng'] = float(row['Longitude'])
                    except (ValueError, KeyError):
                        pass
                vets.append(vet_data)
    except Exception as e:
        print(f"Error loading vets data: {e}")
    
    return vets

def travel_time(latitude, longitude, hospital):
    url = "https://maps.googleapis.com/maps/api/directions/json"

    params = {
        "origin": f"{latitude},{longitude}",
        "destination": hospital,
        "mode": "driving",
        "key": GOOGLE_API_KEY
    }

    r = get(url, params=params)
    r.raise_for_status()
    data = r.json()

    if data["status"] != "OK":
        raise RuntimeError(data["status"])

    leg = data["routes"][0]["legs"][0]

    return {
        "duration": leg["duration"]["value"], # in seconds
        "distance": leg["distance"]["value"]  # in metres
    }

def waiting_time(hospital):
    pass

def get_predicted_wait_time(hospital_name):
    """
    Get predicted wait time for a hospital with soft failing.
    Returns wait time in minutes or None if prediction fails.
    """
    try:
        import pandas as pd
        
        # Load hospital data
        csv_path = os.path.join(os.path.dirname(__file__), 'data', 'hospital_data.csv')
        hospital_df = pd.read_csv(csv_path)
        
        # Find the hospital using fuzzy matching
        matched_name = find_hospital_in_data(hospital_name, hospital_df)
        
        if not matched_name:
            print(f"Could not find hospital '{hospital_name}' in data")
            return None
        
        # Get current time in hours since start of week
        # This is a simplified time counter - adjust as needed
        now = datetime.now()
        current_time = now.hour + (now.weekday() * 24)
        
        # Call run_all with matched hospital name
        wait_multiplier = run_all(matched_name, current_time)
        
        # Get base wait time from dataframe
        hospital_row = hospital_df[hospital_df['hospital_name'] == matched_name].iloc[0]
        base_wait = float(hospital_row['avg_wait_time'])
        
        # Calculate predicted wait time in minutes
        predicted_wait = base_wait * wait_multiplier * 60  # Convert hours to minutes
        
        return round(predicted_wait)
        
    except Exception as e:
        print(f"Error predicting wait time for {hospital_name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def filter_for_specialty(hospitals, specialty):
    pass

@app.route('/api/find-hospital', methods=['POST'])
def find_hospital():
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not latitude or not longitude:
        return jsonify({'status': 'error', 'message': 'Location not provided'}), 400

    try:
        # Get all hospitals and take first 5
        hospitals = get_all_hospitals(latitude, longitude)[:5]

        # Add travel time and wait time info to each hospital
        for hospital in hospitals:
            try:
                time_info = travel_time(latitude, longitude, hospital['address'])
                hospital['duration'] = time_info['duration']
                hospital['distance'] = time_info['distance']
            except Exception as e:
                print(f"Error calculating travel time for {hospital['hospital']}: {e}")
                hospital['duration'] = float('inf')
                hospital['distance'] = 0
            
            # Get predicted wait time for hospitals
            try:
                wait_time_minutes = get_predicted_wait_time(hospital['hospital'])
                hospital['wait_time'] = wait_time_minutes  # in minutes, or None if prediction failed
            except Exception as e:
                print(f"Error getting wait time for {hospital['hospital']}: {e}")
                hospital['wait_time'] = None

        # Sort by combined score: travel time + wait time
        # For hospitals without wait time data, use only travel time
        def get_sort_key(h):
            travel = h['duration']
            wait = h.get('wait_time')
            
            # If wait time is available, combine it with travel time
            # Convert wait time from minutes to seconds and add to travel time
            if wait is not None:
                return travel + (wait * 60)
            else:
                # If no wait time available, just use travel time
                # Add a small penalty to prioritize hospitals with wait time data
                return travel * 1.1
        
        hospitals.sort(key=get_sort_key)

        # Store all 5 hospitals in session
        session['hospitals'] = hospitals
        session['user_location'] = {'latitude': latitude, 'longitude': longitude}
        session['service_type'] = 'hospital'

        return jsonify({'status': 'success', 'hospitals': hospitals})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/find-vet', methods=['POST'])
def find_vet():
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not latitude or not longitude:
        return jsonify({'status': 'error', 'message': 'Location not provided'}), 400

    try:
        import math
        
        def haversine_distance(lat1, lon1, lat2, lon2):
            """Calculate straight-line distance in km using haversine formula"""
            R = 6371  # Earth's radius in km
            lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
            lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
            
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad
            
            a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            return R * c
        
        # Get all vets from CSV (with pre-computed coordinates if available)
        vets = get_all_vets()
        
        if not vets:
            return jsonify({'status': 'error', 'message': 'No vets found'}), 404

        # Filter vets that have coordinates, or geocode the ones that don't
        geocoded_vets = []
        for vet in vets:
            # If coordinates are already available, just calculate distance
            if 'lat' in vet and 'lng' in vet:
                vet['straight_line_distance'] = haversine_distance(
                    latitude, longitude, vet['lat'], vet['lng']
                )
                geocoded_vets.append(vet)
            else:
                # Need to geocode this vet
                try:
                    url = "https://maps.googleapis.com/maps/api/geocode/json"
                    params = {"address": vet['address'], "key": GOOGLE_API_KEY}
                    r = get(url, params=params)
                    r.raise_for_status()
                    geocode_data = r.json()
                    
                    if geocode_data["status"] == "OK" and geocode_data["results"]:
                        location = geocode_data["results"][0]["geometry"]["location"]
                        vet['lat'] = location['lat']
                        vet['lng'] = location['lng']
                        vet['straight_line_distance'] = haversine_distance(
                            latitude, longitude, location['lat'], location['lng']
                        )
                        geocoded_vets.append(vet)
                except Exception as e:
                    print(f"Error geocoding {vet['hospital']}: {e}")
        
        # Sort by straight-line distance and take top 8
        geocoded_vets.sort(key=lambda v: v['straight_line_distance'])
        top_vets = geocoded_vets[:8]
        
        # Now calculate accurate travel time for only the top 8
        for vet in top_vets:
            try:
                time_info = travel_time(latitude, longitude, vet['address'])
                vet['duration'] = time_info['duration']
                vet['distance'] = time_info['distance']
            except Exception as e:
                print(f"Error calculating travel time for {vet['hospital']}: {e}")
                vet['duration'] = float('inf')
                vet['distance'] = 0

        # Sort by actual travel time
        top_vets.sort(key=lambda v: v['duration'])
        
        # Take only the closest 5
        closest_vets = top_vets[:5]

        # Store all 5 vets in session
        session['hospitals'] = closest_vets  # Reuse 'hospitals' key for consistency
        session['user_location'] = {'latitude': latitude, 'longitude': longitude}
        session['service_type'] = 'vet'

        return jsonify({'status': 'success', 'vets': closest_vets})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/alternative-hospitals')
def get_alternative_hospitals():
    """Return the next 4 hospitals (alternatives to the best one)"""
    hospitals = session.get('hospitals', [])
    
    # Return hospitals 2-5 (index 1-4)
    alternatives = hospitals[1:5] if len(hospitals) > 1 else []
    
    return jsonify({
        'status': 'success',
        'hospitals': alternatives
    })

@app.route('/api/select-hospital', methods=['POST'])
def select_hospital():
    """Switch to a different hospital by reordering the session list"""
    data = request.get_json()
    hospital_index = data.get('hospital_index')  # 0-based index
    
    hospitals = session.get('hospitals', [])
    
    if not hospitals or hospital_index is None or hospital_index >= len(hospitals):
        return jsonify({'status': 'error', 'message': 'Invalid hospital index'}), 400
    
    # Move the selected hospital to the front
    selected_hospital = hospitals.pop(hospital_index)
    hospitals.insert(0, selected_hospital)
    
    session['hospitals'] = hospitals
    session.modified = True
    
    return jsonify({'status': 'success', 'hospital': selected_hospital})

@app.route('/api/call-taxi', methods=['POST'])
def call_taxi():
    # To be implemented
    return jsonify({'status': 'success'})

@app.route('/api/get-origin')
def get_origin():
    """Return the user's origin location from session"""
    user_location = session.get('user_location', {})
    
    if user_location and 'latitude' in user_location and 'longitude' in user_location:
        return jsonify({
            'latitude': user_location['latitude'],
            'longitude': user_location['longitude']
        })
    
    return jsonify({'status': 'error', 'message': 'No origin location found'}), 404

@app.route('/api/get-destination')
def get_destination():
    # Check if we have hospitals in session
    hospitals = session.get('hospitals')
    
    if hospitals and len(hospitals) > 0:
        # Use the best hospital (first one after sorting)
        best_hospital = hospitals[0]
        
        # Geocode the hospital address
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": best_hospital['address'],
                "key": GOOGLE_API_KEY
            }
            
            r = get(url, params=params)
            r.raise_for_status()
            geocode_data = r.json()
            
            if geocode_data["status"] == "OK" and geocode_data["results"]:
                location = geocode_data["results"][0]["geometry"]["location"]
                return jsonify({
                    'latitude': location['lat'],
                    'longitude': location['lng'],
                    'name': best_hospital['hospital'],
                    'address': best_hospital['address'],
                    'duration': best_hospital.get('duration'),
                    'distance': best_hospital.get('distance'),
                    'wait_time': best_hospital.get('wait_time')  # Add wait time to response
                })
        except Exception as e:
            print(f"Error geocoding hospital: {e}")

    # Default placeholder (central London)
    return jsonify({
        'latitude': 51.5074,
        'longitude': -0.1278,
        'name': 'Default Destination'
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
