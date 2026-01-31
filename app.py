from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/map')
def map_view():
    return render_template('map.html')

@app.route('/api/find-hospital', methods=['POST'])
def find_hospital():
    # To be implemented
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
