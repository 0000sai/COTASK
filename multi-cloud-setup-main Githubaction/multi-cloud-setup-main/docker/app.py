from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/')
def hello():
    return jsonify({
        "message": "Welcome to Multi-Cloud Demo App",
        "environment": os.getenv("ENVIRONMENT", "development")
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
