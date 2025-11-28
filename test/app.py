from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({"message": "Hello from Flask!", "app": "test"})

@app.route('/api/data', methods=['GET', 'POST'])
def data():
    if request.method == 'POST':
        data = request.json
        return jsonify({"received": data, "status": "success"})
    return jsonify({"data": "Sample data", "status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
