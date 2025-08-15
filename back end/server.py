import requests
import base64
from FetchProcessVisualize import F1BatchScraper
from flask import Flask, jsonify, request
from flask_cors import CORS
from database import F1Database

app = Flask(__name__)
CORS(app, origins="*")

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
            ("FirstPractice", "FP1"),
            ("SecondPractice", "FP2"), 
            ("ThirdPractice", "FP3"),
            ("Qualifying", "Qualifying"),
            ("Sprint", "Sprint"),
            ("SprintQualifying", "Sprint Qualifying")
        ]

        for session_key, session_name in session_types:
            if session_key in race:
                sessions.append(session_name)
        sessions.append("Race")

        return jsonify({"success": True, "sessions": sessions})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/visualizations/<int:round_num>/<string:session>', methods=['GET'])
def get_visualizations(round_num: int, session: str): #lowkey sucks, just pulls premade images from db
    viz_type = request.args.get('type', 'timeline')

    try:
        if round_num < 1 or round_num > 24:
            return jsonify({"success": False, "error": "Round number must be between 1 and 24 for 2025 season"}), 400

        valid_types =["timeline", "histogram"]
        if viz_type not in valid_types:
            return jsonify({"success": False, "error": f"invalid visualizatoin type, must be one of the following: {valid_types}"}), 400
        
        db = F1Database()
        visualizations = []
        vis_bytes = db.get_visualization(session, round_num, 2025, viz_type)

        if vis_bytes:
            visualizations.append({
                "type": viz_type,
                "data": base64.b64encode(vis_bytes).decode('utf-8')
            })


        if visualizations:
            return jsonify({"success": True, "visualizations": visualizations})
        else:
            return jsonify({"success": False, "message": "No visualizations found for this round & session"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/realtime-analysis/<int:round_num>/<string:session>', methods=['POST'])
def realtime_analysis(round_num: int, session: str):
    viz_type = request.args.get('type', 'timeline')
 
    try:
        if round_num < 1 or round_num > 24:
            return jsonify({"success": False, "error": "Round number must be between 1 and 24"}), 400

        valid_types = ["timeline", "histogram"]
        if viz_type not in valid_types:
            return jsonify({"success": False, "error": f"Invalid visualization type. Must be one of: {valid_types}"}), 400

        scraper = F1BatchScraper()
        print(f"Starting real-time analysis for 2025 Round {round_num} {session}")

        success = scraper.execute_scraper(
            2025, 
            round_num, 
            session,
            process_sentiment=True,
            create_visualizations=True,
            save_visualizations=True
        )

        if success:
            db = F1Database()
            vis_bytes = db.get_visualization(session, round_num, 2025, viz_type)

            if vis_bytes:
                return jsonify({
                    "success": True,
                    "message": f"Real-time analysis completed for Round {round_num} {session}",
                    "visualization": {
                        "type": viz_type,
                        "data": base64.b64encode(vis_bytes).decode('utf-8')
                    }
                })
            else:
                return jsonify({
                    "success": True,
                    "message": f"Real-time analysis completed for Round {round_num} {session}, but visualization not found",
                    "warning": "Data was processed but visualization may still be generating"
                })
        else:
            return jsonify({
                "success": False,
                "error": f"Failed to complete real-time analysis for Round {round_num} {session}"
            }), 500
            
    except Exception as e:
        print(f"Error in realtime_analysis: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "api is running smoothly!"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)