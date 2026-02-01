import os

from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, session
from flask.cli import load_dotenv
from requests import get
from urllib.parse import urlparse, parse_qs, unquote

app = Flask(__name__)
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/map')
def map_view():
    place = request.args.get('place', '')
    return render_template('map.html', api_key=GOOGLE_API_KEY, place=place)


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

        # Add travel time info to each hospital
        for hospital in hospitals:
            try:
                time_info = travel_time(latitude, longitude, hospital['address'])
                hospital['duration'] = time_info['duration']
                hospital['distance'] = time_info['distance']
            except Exception as e:
                print(f"Error calculating time for {hospital['hospital']}: {e}")
                hospital['duration'] = float('inf')
                hospital['distance'] = 0

        # Sort by duration (travel time)
        hospitals.sort(key=lambda h: h['duration'])

        # Store all 5 hospitals in session
        session['hospitals'] = hospitals
        session['user_location'] = {'latitude': latitude, 'longitude': longitude}

        return jsonify({'status': 'success', 'hospitals': hospitals})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/find-vet', methods=['POST'])
def find_vet():
    # To be implemented
    return jsonify({'status': 'success'})

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
                    'distance': best_hospital.get('distance')
                })
        except Exception as e:
            print(f"Error geocoding hospital: {e}")
    
    # Fallback: Return coordinates based on optional `place` query parameter
    place = (request.args.get('place') or '').lower()
    if place == 'stonehenge':
        return jsonify({
            'latitude': 51.1789,
            'longitude': -1.8262,
            'name': 'Stonehenge'
        })
    if place == 'bigben' or place == 'big ben':
        return jsonify({
            'latitude': 51.5007,
            'longitude': -0.1246,
            'name': 'Big Ben'
        })

    # Default placeholder (central London)
    return jsonify({
        'latitude': 51.5074,
        'longitude': -0.1278,
        'name': 'Default Destination'
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
