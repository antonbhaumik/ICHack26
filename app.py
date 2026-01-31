from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/hello', methods=['GET'])
def hello():
    name = request.args.get('name', 'World')
    return jsonify({'message': f'Hello, {name}!'})

@app.route('/api/data', methods=['POST'])
def post_data():
    data = request.get_json()
    # Process your data here
    return jsonify({'status': 'success', 'received': data})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
