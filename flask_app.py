from flask import Flask, request, jsonify
from datetime import datetime
import pika
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
        with open('/app/expenses_backup.txt', 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except FileNotFoundError:
        return 'No expenses yet', 404


@app.route('/api/expenses/save', methods=['POST'])
def add_expense():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid or empty JSON'}), 400
            
        app.logger.info(f"📥 Получен запрос с данными: {data}")
        
        required_fields = ['date', 'userUid', 'sum', 'category', 'subcategory']
        for field in required_fields:
            if field not in data:
                app.logger.warning(f"Отсутствует обязательное поле: {field}")
                return jsonify({'error': f'Missing field: {field}'}), 400
        
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
            return jsonify({'status': 'success', 'message': 'Sent via AMQP'}), 200
        else:
            app.logger.warning("⚠️ Не удалось отправить в RabbitMQ, сохраняем в резервный файл")
            payload = json.dumps(message, ensure_ascii=False)
            with open('/app/expenses_backup.txt', 'a', encoding='utf-8') as f:
                f.write(payload + '\n')
            return jsonify({'status': 'success', 'message': 'Saved to file (backup)'}), 200

    except Exception as e:
        app.logger.error(f"❌ Критическая ошибка в обработчике: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

def send_to_rabbitmq(message: dict) -> bool:
    connection = None
    try:
        user_uid = message.get('userUid')
        queue_name = f"budget_events_{user_uid}"
        
        amqp_url = f"amqps://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}/{RABBITMQ_VHOST}"
        params = pika.URLParameters(amqp_url)
        params.socket_timeout = 10
        params.blocked_connection_timeout = 10
        
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message, ensure_ascii=False),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        return True
    except Exception as e:
        app.logger.error(f"❌ RabbitMQ AMQP ошибка: {e}", exc_info=True)
        return False
    finally:
        if connection and not connection.is_closed:
            connection.close()

# Для gunicorn — ЭТО ОБЯЗАТЕЛЬНО!
application = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
