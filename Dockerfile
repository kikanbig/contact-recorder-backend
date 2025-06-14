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

# Копируем Python requirements и устанавливаем зависимости поэтапно
COPY requirements.txt ./
RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Устанавливаем базовые зависимости сначала
RUN python3 -m pip install --no-cache-dir torch>=1.12.0,<2.0.0 torchaudio>=0.12.0,<2.0.0

# Устанавливаем основные зависимости
RUN python3 -m pip install --no-cache-dir numpy ffmpeg-python librosa soundfile transformers>=4.21.0

# Устанавливаем WhisperX
RUN python3 -m pip install --no-cache-dir whisperx

# Устанавливаем зависимости для диаризации
RUN python3 -m pip install --no-cache-dir huggingface_hub datasets omegaconf hydra-core accelerate

# Устанавливаем pyannote.audio и speechbrain последними (самые проблемные)
RUN python3 -m pip install --no-cache-dir speechbrain>=0.5.0
RUN python3 -m pip install --no-cache-dir pyannote.audio==3.1.1

# Копируем исходный код приложения
COPY . .

# Создаем директорию для загрузок
RUN mkdir -p uploads

# Экспортируем порт
EXPOSE 3000

# Запускаем приложение
CMD ["npm", "start"] 