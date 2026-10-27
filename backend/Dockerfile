FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements.lock.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./backend/app
COPY data/bills.json ./data/bills.json
ENV APP_MODE=production
ENV PYTHONPATH=/srv/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
