from flask import Flask, request, jsonify
from datetime import datetime
import requests
import json
import os
import logging
from logging import FileHandler

app = Flask(__name__)

RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'owrqpdlu')
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASSWORD', '10vJ9kVWgSsee7029maNq8xNSeQUN47F')
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'lizard.lmq.cloudamqp.com')
RABBITMQ_VHOST = os.environ.get('RABBITMQ_VHOST', 'owrqpdlu')

# Настройка логов: в файл И в консоль (stdout)
file_handler = FileHandler('app.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

@app.route('/health', methods=['GET'])
def health():
    return 'OK'

@app.route('/api/expenses/list', methods=['GET'])
def get_expenses():
    try:
        with open('/app/expenses_backup.txt', 'r') as f:
            return f.read(), 200, {'Content-Type': 'text/plain'}
    except:
        return 'No expenses yet', 404

@app.route('/api/expenses/save', methods=['POST'])
def add_expense():
    try:
        # Получаем JSON из тела запроса
        data = request.get_json()
        app.logger.info(f"📥 Получен запрос с данными: {data}")
        
        # Проверяем обязательные поля
        required_fields = ['date', 'userUid', 'sum', 'category', 'subcategory']
        for field in required_fields:
            if field not in data:
                app.logger.warning(f"Отсутствует обязательное поле: {field}")
                return jsonify({'error': f'Missing field: {field}'}), 400
        
        # Формируем сообщение для RabbitMQ
        message = {
            'date': data['date'],
            'userUid': data['userUid'],
            'userName': data.get('userName', ''),
            'sum': float(data['sum']),
            'category': data['category'],
            'subcategory': data['subcategory'],
            'timestamp': datetime.now().isoformat()
        }
        
        if send_to_rabbitmq(message):
            app.logger.info("✅ Сообщение успешно отправлено в RabbitMQ")
            return jsonify({'status': 'success', 'message': 'Sent via HTTP API'}), 200
        else:
            app.logger.error(f"❌ Критическая ошибка в обработчике: {e}", exc_info=True)
            with open('/app/expenses_backup.txt', 'a') as f:
                f.write(payload + '\n')
            return jsonify({'status': 'success', 'message': 'Saved to file (backup)'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def send_to_rabbitmq(message):
    try:
        url = f'https://{RABBITMQ_HOST}/api/exchanges/{RABBITMQ_VHOST}/amq.default/publish'
        
        payload = {
            'properties': {},
            'routing_key': 'expenses_events',
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
        app.logger.error(f"RabbitMQ ошибка: {e}")  #пишем в файл app.log
        return False

# Для gunicorn — ЭТО ОБЯЗАТЕЛЬНО!
application = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
