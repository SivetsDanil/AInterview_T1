
FROM python:3.11-slim


LABEL maintainer="sivets.one@gmail.com"
LABEL description="SciBox Interview — AI-powered coding interview platform"

# 📁 Рабочая директория внутри контейнера
WORKDIR /app

# 📥 Копируем зависимости и устанавливаем их (кешируем слой)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 📤 Копируем ВЕСЬ проект
COPY . .

# 🔒 Безопасность: убираем debug, задаём порт
ENV FLASK_ENV=production
ENV FLASK_APP=main.py

# 🌐 Порт
EXPOSE 5000

# 🚀 Запуск через Gunicorn (production-ready WSGI)
# --bind 0.0.0.0:5000 — слушать все интерфейсы
# --workers 2 — 2 процесса (для dev достаточно)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "main:app"]