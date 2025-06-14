# Используем Ubuntu образ для лучшей совместимости с Python библиотеками
FROM ubuntu:22.04

# Предотвращаем интерактивные запросы во время установки
ENV DEBIAN_FRONTEND=noninteractive

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    python3-pip \
    python3-dev \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Node.js 18
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Создаем рабочую директорию
WORKDIR /app

# Копируем package.json и package-lock.json
COPY package*.json ./

# Устанавливаем Node.js зависимости
RUN npm ci --only=production

# Обновляем pip и базовые инструменты
RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel

# ПОЭТАПНАЯ УСТАНОВКА PYTHON ЗАВИСИМОСТЕЙ ДЛЯ ДИАГНОСТИКИ

# Шаг 1: Устанавливаем PyTorch (самый важный)
RUN echo "🔥 Шаг 1: Устанавливаем PyTorch..." && \
    python3 -m pip install --no-cache-dir torch>=1.12.0,<2.0.0 torchaudio>=0.12.0,<2.0.0

# Шаг 2: Устанавливаем базовые зависимости
RUN echo "🔥 Шаг 2: Устанавливаем базовые зависимости..." && \
    python3 -m pip install --no-cache-dir numpy ffmpeg-python librosa soundfile

# Шаг 3: Устанавливаем Transformers
RUN echo "🔥 Шаг 3: Устанавливаем Transformers..." && \
    python3 -m pip install --no-cache-dir "transformers>=4.21.0"

# Шаг 4: Устанавливаем WhisperX (основная библиотека)
RUN echo "🔥 Шаг 4: Устанавливаем WhisperX..." && \
    python3 -m pip install --no-cache-dir whisperx

# Шаг 5: Устанавливаем зависимости для диаризации
RUN echo "🔥 Шаг 5: Устанавливаем зависимости для диаризации..." && \
    python3 -m pip install --no-cache-dir huggingface_hub datasets

# Шаг 6: Устанавливаем конфигурационные библиотеки
RUN echo "🔥 Шаг 6: Устанавливаем конфигурационные библиотеки..." && \
    python3 -m pip install --no-cache-dir omegaconf hydra-core

# Шаг 7: Устанавливаем accelerate
RUN echo "🔥 Шаг 7: Устанавливаем accelerate..." && \
    python3 -m pip install --no-cache-dir accelerate

# Шаг 8: Устанавливаем SpeechBrain (может быть проблемным)
RUN echo "🔥 Шаг 8: Устанавливаем SpeechBrain..." && \
    python3 -m pip install --no-cache-dir "speechbrain>=0.5.0"

# Шаг 9: Устанавливаем pyannote.audio (самый проблемный)
RUN echo "🔥 Шаг 9: Устанавливаем pyannote.audio..." && \
    python3 -m pip install --no-cache-dir pyannote.audio==3.1.1

# Копируем исходный код приложения
COPY . .

# Создаем директорию для загрузок
RUN mkdir -p uploads

# Экспортируем порт
EXPOSE 3000

# Запускаем приложение
CMD ["npm", "start"] 