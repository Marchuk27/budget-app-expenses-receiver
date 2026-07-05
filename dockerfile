FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY flask_app.py .

EXPOSE 8000

CMD ["gunicorn", "flask_app:application", "--bind", "0.0.0.0:8000"]