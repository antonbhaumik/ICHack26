import logging
import os

from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify
from flask.cli import load_dotenv
from requests import get
from urllib.parse import urlparse, parse_qs, unquote

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

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
        logger.info(f"Location received: Latitude={latitude}, Longitude={longitude}")
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

    logger.info(f"Finding hospital near: Latitude={latitude}, Longitude={longitude}")

    return jsonify({'status': 'success'})

@app.route('/api/find-vet', methods=['POST'])
def find_vet():
    # To be implemented
    return jsonify({'status': 'success'})

@app.route('/api/call-taxi', methods=['POST'])
def call_taxi():
    # To be implemented
    return jsonify({'status': 'success'})

@app.route('/api/get-destination')
def get_destination():
    # Return coordinates based on optional `place` query parameter
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
