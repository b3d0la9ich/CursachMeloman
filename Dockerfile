# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . .

# Устанавливаем зависимости
RUN pip install --upgrade pip && pip install -r requirements.txt

# Указываем порт (Flask использует 5000)
EXPOSE 5000

# Команда запуска приложения
CMD ["python", "app.py"]
