from flask import Flask, request, jsonify
from datetime import datetime
import requests
import json
import os

app = Flask(__name__)

RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'owrqpdlu')
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASSWORD', '10vJ9kVWgSsee7029maNq8xNSeQUN47F')
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'lizard.lmq.cloudamqp.com')
RABBITMQ_VHOST = os.environ.get('RABBITMQ_VHOST', 'owrqpdlu')

def send_to_rabbitmq(message):
    try:
        url = f'https://{RABBITMQ_HOST}/api/queues/{RABBITMQ_VHOST}/expenses_queue/publish'
        
        payload = {
            'properties': {},
            'routing_key': 'expenses_queue',
            'payload': json.dumps(message, ensure_ascii=False),
            'payload_encoding': 'string'
        }
        
        response = requests.post(
            url,
            auth=(RABBITMQ_USER, RABBITMQ_PASSWORD),
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        return response.status_code == 200
    except Exception as e:
        print(f"RabbitMQ ошибка: {e}")
        return False

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    try:
        payload = request.data.decode('utf-8').strip()
        print(f"Получено: {payload}")

        parts = payload.split(':')
        if len(parts) != 4:
            return jsonify({'error': 'Invalid format'}), 400

        message = {
            'date': parts[0],
            'category': parts[1],
            'subcategory': parts[2],
            'amount': float(parts[3]),
            'timestamp': datetime.now().isoformat()
        }
        
        if send_to_rabbitmq(message):
            return jsonify({'status': 'success', 'message': 'Sent via HTTP API'}), 200
        else:
            with open('/app/expenses_backup.txt', 'a') as f:
                f.write(payload + '\n')
            return jsonify({'status': 'success', 'message': 'Saved to file (backup)'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return 'OK'

@app.route('/expenses', methods=['GET'])
def get_expenses():
    try:
        with open('/app/expenses_backup.txt', 'r') as f:
            return f.read(), 200, {'Content-Type': 'text/plain'}
    except:
        return 'No expenses yet', 404

# Для gunicorn — ЭТО ОБЯЗАТЕЛЬНО!
application = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
