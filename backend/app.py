import threading
import uuid
import os
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import numpy as np
from .engine import SeismicEngine, escribir_video_mp4

app = Flask(__name__)
CORS(app)

engine = SeismicEngine()

current_simulation = {
    "stations": [],
    "observed": [],
    "real_source": [50, 50, 10],
    "real_A0": 1000,
    "curva_error_minimo": [],
}

video_jobs = {}


def _run_video_job(job_id, observed, A0, z_range, num_cuts, fps, grid_size):
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    video_path = os.path.join(output_dir, f'cortes_z_{job_id}.mp4')

    video_jobs[job_id].update({'state': 'running', 'message': 'Generando frames...', 'progress': 0})

    frames_dir = os.path.join(output_dir, f'frames_{job_id}')
    frame_paths = []

    try:
        os.makedirs(frames_dir, exist_ok=True)

        video_jobs[job_id].update({
            'progress': 2,
            'message': 'Evaluando cortes Z (E_min + mapas)...',
        })
        meta = engine.procesar_secuencia_cortes_z(
            observed, A0, z_range, num_cuts,
            grid_size=grid_size, x_range=(-70, 70), y_range=(-70, 70),
            cache_grids=True,
        )
        curva = meta['curva_error_minimo']
        current_simulation['curva_error_minimo'] = curva
        video_jobs[job_id]['curva_error_minimo'] = curva

        for idx, (z_plane, X, Y, Z) in enumerate(meta['grid_cache']):
            frame_path = os.path.join(frames_dir, f'frame_{idx:04d}.png')
            engine.save_heatmap_frame_from_grid(
                X, Y, Z, z_plane, frame_path,
                contour_levels=meta['levels'],
                log_vmin=meta['z_lo'],
                log_vmax=meta['z_hi'],
            )
            frame_paths.append(frame_path)
            progress = int(((idx + 1) / num_cuts) * 90)
            video_jobs[job_id].update({
                'progress': progress,
                'message': f'Frame {idx + 1}/{num_cuts} (z={z_plane:.1f}m)',
            })

        video_jobs[job_id].update({'progress': 92, 'message': 'Uniendo video MP4...'})
        escribir_video_mp4(frame_paths, video_path, fps=fps)

        video_jobs[job_id].update({
            'state': 'done',
            'progress': 100,
            'message': 'Video listo',
            'path': video_path,
        })
    except Exception as exc:
        video_jobs[job_id].update({'state': 'error', 'message': str(exc), 'progress': 0})
    finally:
        for frame_path in frame_paths:
            if os.path.isfile(frame_path):
                os.remove(frame_path)
        if os.path.isdir(frames_dir) and not os.listdir(frames_dir):
            os.rmdir(frames_dir)


@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({"status": "ready", "message": "Motor sísmico operativo"})


@app.route('/api/simulate', methods=['POST'])
def simulate_custom():
    data = request.json or {}
    stations = np.array(data.get('stations', []), dtype=float)
    amplitudes = np.array(data.get('amplitudes', []), dtype=float)

    if len(stations) == 0 or len(amplitudes) == 0:
        return jsonify({"error": "Faltan estaciones o amplitudes"}), 400
    if len(stations) != len(amplitudes):
        return jsonify({"error": "Estaciones y amplitudes no coinciden"}), 400

    engine.stations = stations
    current_simulation["stations"] = stations
    current_simulation["observed"] = amplitudes
    current_simulation["real_source"] = [
        float(data.get('x', 0)),
        float(data.get('y', 0)),
        float(data.get('z', 10)),
    ]
    current_simulation["real_A0"] = float(data.get('a0', 1000))
    engine.alpha = float(data.get('alpha', 5)) / 100.0

    return jsonify({"status": "success", "stations_count": len(stations)})


@app.route('/api/solve', methods=['POST'])
def solve_localization():
    if len(current_simulation["observed"]) == 0:
        return jsonify({"error": "No simulation data"}), 400

    res = engine.solve(current_simulation["observed"])
    if res.success:
        return jsonify({
            "estimated_pos": res.x[:3].tolist(),
            "estimated_A0": float(res.x[3]),
            "residual_error": float(res.fun),
            "success": True,
        })
    return jsonify({"error": "Optimization failed", "success": False}), 400


@app.route('/api/heatmap-video/start', methods=['POST'])
def start_heatmap_video():
    if len(current_simulation["observed"]) == 0:
        return jsonify({"error": "No simulation data"}), 400

    data = request.json or {}
    job_id = str(uuid.uuid4())[:8]
    z_min = float(data.get('z_min', 1))
    z_max = float(data.get('z_max', 200))
    num_cuts = max(int(data.get('num_cuts', 100)), 100)
    A0 = float(data.get('a0', current_simulation["real_A0"]))
    fps = int(data.get('fps', 10))

    video_jobs[job_id] = {'state': 'queued', 'progress': 0, 'message': 'En cola...', 'path': None}

    thread = threading.Thread(
        target=_run_video_job,
        args=(job_id, current_simulation["observed"], A0, (z_min, z_max), num_cuts, fps, 40),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route('/api/error-minimo-z', methods=['POST'])
def error_minimo_z():
    if len(current_simulation["observed"]) == 0:
        return jsonify({"error": "No hay datos de simulación"}), 400

    data = request.json or {}
    A0 = float(data.get('a0', current_simulation["real_A0"]))
    z_min = float(data.get('z_min', 1))
    z_max = float(data.get('z_max', 200))
    num_cuts = max(int(data.get('num_cuts', 50)), 2)
    grid_size = int(data.get('grid_size', 40))

    curva = engine.calcular_curva_error_minimo_z(
        current_simulation["observed"],
        A0,
        z_range=(z_min, z_max),
        num_cuts=num_cuts,
        grid_size=grid_size,
    )
    curva = sorted(curva, key=lambda p: p['z'])
    current_simulation['curva_error_minimo'] = curva

    punto_min = None
    if curva:
        punto_min = min(curva, key=lambda p: p['error'])

    return jsonify({
        "curva_error_minimo": curva,
        "z_minimo_curva": punto_min['z'] if punto_min else None,
        "error_minimo": punto_min['error'] if punto_min else None,
    })


@app.route('/api/heatmap-video/status/<job_id>', methods=['GET'])
def video_status(job_id):
    job = video_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Trabajo no encontrado"}), 404
    payload = {
        "state": job.get('state'),
        "progress": job.get('progress', 0),
        "message": job.get('message', ''),
    }
    if job.get('curva_error_minimo'):
        payload['curva_error_minimo'] = job['curva_error_minimo']
    return jsonify(payload)


@app.route('/api/heatmap-video/download/<job_id>', methods=['GET'])
def video_download(job_id):
    job = video_jobs.get(job_id)
    if not job or job.get('state') != 'done' or not job.get('path'):
        return jsonify({"error": "Video no disponible"}), 404
    return send_file(job['path'], mimetype='video/mp4', as_attachment=True, download_name='cortes_z.mp4')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
