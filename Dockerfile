# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY package*.json ./
COPY requirements.txt ./
COPY requirements_speechbrain.txt ./
COPY *.py ./
COPY *.js ./

# Копируем папку admin отдельно
COPY admin/ ./admin/

# Устанавливаем Node.js зависимости
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    npm install && \
    rm -rf /var/lib/apt/lists/*

# Обновляем pip и устанавливаем wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Шаг 1: Проверяем Python и pip
RUN echo "🐍 УСТАНОВКА PYTHON ЗАВИСИМОСТЕЙ" && \
    python -c "import sys; print(f'Python версия: {sys.version}')"

# Шаг 2: Устанавливаем PyTorch CPU
RUN echo "🔥 Шаг 2: Установка PyTorch CPU..." && \
    python -m pip install torch==2.1.0+cpu torchvision==0.16.0+cpu torchaudio==2.1.0+cpu -f https://download.pytorch.org/whl/torch_stable.html && \
    python -c "import torch; print(f'✅ PyTorch {torch.__version__} установлен')"

# Шаг 3: Устанавливаем базовые зависимости
RUN echo "📦 Шаг 3: Установка базовых зависимостей..." && \
    python -m pip install numpy==1.24.3 scipy==1.11.1 && \
    python -c "import numpy, scipy; print('✅ NumPy и SciPy установлены')"

# Шаг 4: Устанавливаем аудио библиотеки
RUN echo "🎵 Шаг 4: Установка аудио библиотек..." && \
    python -m pip install librosa==0.10.1 soundfile==0.12.1 && \
    python -c "import librosa, soundfile; print('✅ Аудио библиотеки установлены')"

# Шаг 5: Устанавливаем Transformers
RUN echo "🤖 Шаг 5: Установка Transformers..." && \
    python -m pip install transformers==4.35.0 tokenizers==0.14.1 && \
    python -c "import transformers; print('✅ Transformers установлен')"

# Шаг 6: Устанавливаем faster-whisper
RUN echo "🎤 Шаг 6: Установка faster-whisper..." && \
    python -m pip install faster-whisper==0.9.0 && \
    python -c "import faster_whisper; print('✅ faster-whisper установлен')"

# Шаг 8: Устанавливаем SpeechBrain для диаризации
RUN echo "🧠 Шаг 8: Установка SpeechBrain для диаризации..." && \
    python -m pip install speechbrain==0.5.16 && \
    python -m pip install pyannote.audio==3.1.1 && \
    python -c "import speechbrain; print('✅ SpeechBrain установлен')" && \
    python -c "import pyannote.audio; print('✅ pyannote.audio установлен')"

# Шаг 9: Финальная проверка всех компонентов
RUN echo "✅ Шаг 9: Финальная проверка компонентов..." && \
    python -c "import sys; print('🔍 ФИНАЛЬНАЯ ДИАГНОСТИКА:'); import torch; print(f'✅ PyTorch: {torch.__version__}'); import faster_whisper; print('✅ faster-whisper: импортирован'); import librosa; print(f'✅ librosa: {librosa.__version__}'); import transformers; print(f'✅ transformers: {transformers.__version__}'); import speechbrain; print('✅ SpeechBrain: импортирован'); import pyannote.audio; print('✅ pyannote.audio: импортирован'); print('🎉 Диагностика завершена!')"

# Создаем директории для загрузок и записей
RUN mkdir -p uploads records

# Проверяем что папка admin скопировалась
RUN echo "📁 Проверяем структуру файлов:" && \
    ls -la && \
    echo "📂 Содержимое admin:" && \
    ls -la admin/ || echo "❌ Папка admin не найдена"

# Открываем порт
EXPOSE 3000

# Запускаем сервер
CMD ["node", "server.js"] 