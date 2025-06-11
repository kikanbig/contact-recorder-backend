# 🎙️ Contact Recorder Backend - Версия 0.1

Node.js backend с PostgreSQL для системы записи переговоров продавцов.

## 🎯 Версия 0.1 - Стабильная

### ✅ Рабочие функции:
- Загрузка аудио файлов от мобильного приложения
- PostgreSQL база данных на Railway
- Веб админ панель (admin/admin123)
- Браузерная транскрипция через Speech Recognition API
- Fallback на OpenAI Whisper (при наличии API ключа)
- JWT аутентификация
- Управление пользователями и локациями

### 🔧 Исправленные проблемы:
- GraphQL multipart конфликт при загрузке
- Обработка ошибок OpenAI API (квота, биллинг)
- Правильная работа с Bearer токенами
- Валидация данных и безопасность

## 🚀 Деплой

Автоматический деплой на Railway: https://contact-recorder-backend-production.up.railway.app

### Админ панель:
- URL: https://contact-recorder-backend-production.up.railway.app/admin/
- Логин: admin / admin123

## 🎙️ Транскрипция

### Браузерная (бесплатная):
- Web Speech Recognition API
- Поддержка русского языка
- Работает в Chrome/Edge

### OpenAI Whisper (платная):
- Требует OPENAI_API_KEY
- Высокое качество транскрипции
- $0.006 за минуту аудио

## 📡 API Endpoints

### Аутентификация
- `POST /api/auth/login` - Вход
- `POST /api/auth/register` - Регистрация

### Записи
- `POST /api/recordings/upload` - Загрузка аудио
- `GET /api/recordings` - Список записей
- `GET /api/recordings/:id` - Детали записи
- `POST /api/recordings/:id/transcribe` - OpenAI транскрипция
- `POST /api/recordings/:id/transcribe-text` - Сохранение браузерной транскрипции

### Статистика
- `GET /api/recordings/stats` - Статистика записей

## 🔧 Настройка

### Переменные окружения:
```env
DATABASE_URL=postgresql://...
JWT_SECRET=your-secret-key
OPENAI_API_KEY=sk-... (опционально)
```

### Локальный запуск:
```bash
npm install
npm run dev
```

## 🔗 Связанные репозитории
- Мобильное приложение: [21vek-contact-recorder-app](https://github.com/kikanbig/21vek-contact-recorder-app)

## 📱 APK для тестирования
[Скачать APK](https://expo.dev/accounts/kikanbig/projects/21vek-contact-recorder)

---
**Версия**: 0.1  
**Дата**: Июнь 2025  
**Статус**: Стабильная рабочая версия ✅
