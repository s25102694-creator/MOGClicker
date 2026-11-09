# Используем официальный облегченный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл с зависимостями и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь остальной код проекта
COPY . .

# Открываем порт, который использует RelaxDev
EXPOSE 8080

# Команда для запуска приложения через Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
