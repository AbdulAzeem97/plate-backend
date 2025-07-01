from flask import Flask, request, jsonify
from flask_cors import CORS

from celery_config import celery_app
from celery import states
from plate_tasks import run_plate_optimization

app = Flask(__name__)
CORS(app)

@app.route('/optimize-plates', methods=['POST'])
def optimize_plates():
    data = request.get_json()
    task = run_plate_optimization.delay(data) # async call to background task
    return jsonify({'task_id': task.id}), 202

@app.route("/", methods=["GET"])
def hello():
    return "Backend is up and running!"

@app.route('/task-status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = celery_app.AsyncResult(task_id)

    if task.state == states.PENDING:
        return jsonify({'status': 'pending'}), 202
    elif task.state == 'PROGRESS':
        return jsonify({
            'status': 'progress',
            'meta': task.info
        }), 202
    elif task.state == states.SUCCESS:
        return jsonify(task.result), 200
    elif task.state == states.FAILURE:
        return jsonify({'status': 'failed', 'error': str(task.info)}), 500
    else:
        return jsonify({'status': task.state}), 202


if __name__ == '__main__':
    app.run(host='192.168.2.57', port=5200, debug=True)