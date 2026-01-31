import logging

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/map')
def map_view():
    return render_template('map.html')


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

def get_all_hospitals(location):
    pass

def travel_time(hospital):
    pass

def waiting_time(hospital):
    pass

def filter_for_specialty(hospitals, specialty):
    pass

def filter_for_opening_time(hospitals):
    pass


@app.route('/api/find-hospital', methods=['POST'])
def find_hospital():
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    logger.info(f"Finding hospital near: Latitude={latitude}, Longitude={longitude}")

    return jsonify({'status': 'success'})

@app.route('/api/find-specialist', methods=['POST'])
def find_specialist():
    # To be implemented
    hospital_type = request.get_json().get('type')
    return jsonify({'status': 'success', 'type': hospital_type})

@app.route('/api/call-taxi', methods=['POST'])
def call_taxi():
    # To be implemented
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
