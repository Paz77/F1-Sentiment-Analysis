import requests
import base64
from flask import Flask, jsonify
from flask_cors import CORS
from database import F1Database

app = Flask(__name__)
CORS(app)

@app.route('/api/races', methods=['GET']) 
def get_races():
    try:
        response = requests.get("https://api.jolpi.ca/ergast/f1/2025.json")
        response.raise_for_status()

        data = response.json()
        races = data["MRData"]["RaceTable"]["Races"]

        race_list = []
        for race in races:
            race_info = {
                "round": race["round"],
                "name": race["raceName"]
            }
            race_list.append(race_info)
        
        return jsonify({"success": True, "races": race_list})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/sessions/<int:round_num>', methods=['GET'])
def get_sessions(round_num: int):
    try:
        if round_num < 1 or round_num > 24:
            return jsonify({"success": False, "error": "Round number must be between 1 and 24 for 2025 season"}), 400

        url = f"https://api.jolpi.ca/ergast/f1/2025/{round_num}.json"
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        race = data["MRData"]["RaceTable"]["Races"][0]

        sessions = []
        session_types = [
            "FirstPractice",
            "SecondPractice",
            "ThirdPractice",
            "Qualifying",
            "Sprint",
            "SprintQualifying"
        ]

        for session in session_types:
            if session in race:
                sessions.append(session)
        sessions.append("Race")

        return jsonify({"success": True, "sessions": sessions})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/visualizations/<int:round_num>/<string:session>', methods=['GET'])
def get_visualizations(round_num: int, session: str):
    try:
        if round_num < 1 or round_num > 24:
            return jsonify({"success": False, "error": "Round number must be between 1 and 24 for 2025 season"}), 400
        
        db = F1Database()
        visualizations = []

        for vis_type in ["histogram", "timeline"]:
            vis_bytes = db.get_visualization(session, round_num, 2025, vis_type)
            if vis_bytes:
                vis_base64 = base64.b64encode(vis_bytes).decode('utf-8')
                visualizations.append({
                    "type": vis_type,
                    "data": vis_base64
                })

        if visualizations:
            return jsonify({"success": True, "visualizations": visualizations})
        else:
            return jsonify({"success": False, "message": "No visualizations found for this round & session"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "api is running smoothly!"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)