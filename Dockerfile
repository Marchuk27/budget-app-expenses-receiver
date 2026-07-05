FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY flask_app.py .

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "flask_app:app"] 
