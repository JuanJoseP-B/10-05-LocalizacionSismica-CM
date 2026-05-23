from flask import Flask, jsonify, request
from flask_cors import CORS
import numpy as np
from .engine import SeismicEngine

app = Flask(__name__)
CORS(app)

# Global engine instance
engine = SeismicEngine()

# State storage for the current simulation
current_simulation = {
    "stations": [],
    "observed": [],
    "real_source": [50, 50, 10],
    "real_A0": 1000
}

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({"status": "ready", "message": "Motor sísmico operativo"})

@app.route('/api/setup', methods=['POST'])
def setup_simulation():
    data = request.json
    x = float(data.get('x', 50))
    y = float(data.get('y', 50))
    z = float(data.get('z', 10))
    a0 = float(data.get('a0', 1000))
    n_stations = int(data.get('n_stations', 8))
    
    current_simulation["real_source"] = [x, y, z]
    current_simulation["real_A0"] = a0
    current_simulation["stations"] = engine.generate_stations(count=n_stations)
    current_simulation["observed"] = engine.simulate_signal([x, y, z], a0)
    
    return jsonify({"status": "success", "stations_count": n_stations})

@app.route('/api/stations', methods=['GET'])
def get_stations():
    return jsonify({
        "stations": current_simulation["stations"].tolist(),
        "real_source": current_simulation["real_source"],
        "real_A0": current_simulation["real_A0"]
    })

@app.route('/api/solve', methods=['POST'])
def solve_localization():
    if len(current_simulation["observed"]) == 0:
        return jsonify({"error": "No simulation data"}), 400
        
    res = engine.solve(current_simulation["observed"])
    if res.success:
        return jsonify({
            "estimated_pos": res.x[:3].tolist(),
            "estimated_A0": res.x[3],
            "error": res.fun
        })
    return jsonify({"error": "Optimization failed"}), 400

@app.route('/api/heatmap', methods=['GET'])
def get_heatmap():
    z = float(request.args.get('z', current_simulation["real_source"][2]))
    X, Y, Z = engine.get_heatmap_data(z, current_simulation["observed"], current_simulation["real_A0"], grid_size=30)
    return jsonify({
        "x": X[0, :].tolist(),
        "y": Y[:, 0].tolist(),
        "z_values": Z.tolist()
    })

@app.route('/api/error-curve', methods=['GET'])
def get_error_curve():
    z_vals, e_vals = engine.get_global_error_curve(current_simulation["observed"], current_simulation["real_A0"], z_range=(0, 50), steps=30)
    return jsonify({
        "z": z_vals.tolist(),
        "error": e_vals.tolist()
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
