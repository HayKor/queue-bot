FROM python:3.14-slim
# Копируем uv из официального образа
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Переменные окружения для оптимизации Python в Docker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Копируем файлы зависимостей
# Контекст сборки будет корень проекта, поэтому пути прямые
COPY pyproject.toml uv.lock ./

# 2. Устанавливаем зависимости
# Используем --system, так как в контейнере нам не нужен venv.
# Команда 'uv sync' или 'uv pip install' подтянет всё из pyproject.toml
RUN uv pip install --system --no-cache -r pyproject.toml || uv pip install --system --no-cache .

# 3. Копируем весь код проекта
# .dockerignore должен игнорировать venv и pycache
COPY . .

# Проверяем, что папка data существует для SQLite
RUN mkdir -p /app/data

# Запускаем через python3
CMD ["python3", "main.py"]
