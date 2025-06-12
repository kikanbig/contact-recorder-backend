# Используем официальный Node.js образ с Alpine Linux для меньшего размера
FROM node:18-alpine

# Устанавливаем системные зависимости включая Python и FFmpeg
RUN apk update && apk add --no-cache \
    python3 \
    py3-pip \
    ffmpeg \
    git \
    build-base \
    python3-dev \
    linux-headers

# Создаем рабочую директорию
WORKDIR /app

# Копируем package.json и package-lock.json
COPY package*.json ./

# Устанавливаем Node.js зависимости
RUN npm ci --only=production

# Копируем Python requirements
COPY requirements.txt ./

# Устанавливаем Python зависимости
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY . .

# Создаем директорию для загрузок
RUN mkdir -p uploads

# Экспортируем порт
EXPOSE 3000

# Запускаем приложение
CMD ["npm", "start"] 