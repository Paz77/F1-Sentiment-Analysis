from flask import Flask, jsonify
from flask_cors import CORS
from database import F1Database

app = Flask(__name__)
CORS(app)

@app.route('/api/races') #aka round nums
def get_races():
    try:
        races = []
        
        return jsonify({"success": True, "races": races})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/sessions')
def get_sessions(round_num: int):
    try:
        sessions = []
        #add stuff here

        return jsonify({"success": True, "sessions": sessions})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/visualizations')
def get_visualizations():
    try:
        db = F1Database()
        visualizations = []
        #add stuff here

        return jsonify({"success": True, "visualizations": visualizations})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health_check():
    return jsonify({"status": "healthy", "message": "api is running smoothly!"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)