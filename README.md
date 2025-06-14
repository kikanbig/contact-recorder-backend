# 🎙️ Contact Recorder Backend - Версия 1.0 (Whisper)

Node.js backend с PostgreSQL для системы записи переговоров продавцов.

## 🎯 Версия 1.0 - Стабильная с Whisper

### ✅ Основные функции:
- **Загрузка аудио файлов** от мобильного приложения
- **PostgreSQL база данных** на Railway
- **Веб админ панель** с современной тёмной темой
- **Локальная транскрипция** через OpenAI Whisper
- **Выбор моделей Whisper** (tiny, base, small, medium, large)
- **JWT аутентификация** и управление пользователями
- **Массовое удаление записей** с чекбоксами
- **Система диагностики** Whisper/Python/FFmpeg
- **Исправлены конфликты маршрутов** Express

### 🎯 Качество транскрипции:
- **Модель по умолчанию**: `small` (рекомендуется для русского языка)
- **Поддержка всех моделей**: tiny, base, small, medium, large
- **Детальная диагностика ошибок** с логированием
- **Выбор модели** в админ-панели для каждой записи

### 🔧 Исправленные проблемы:
- Конфликт маршрутов `/stats` vs `/:id`
- Дублирование JSON вывода в Python скрипте
- Unicode ошибки в транскрипции
- Браузерная транскрипция (заменена на серверную)
- Проблемы с парсингом JSON ответов

## 🚀 Деплой

**Автоматический деплой на Railway**: https://contact-recorder-backend-production.up.railway.app

### Админ панель:
- **URL**: https://contact-recorder-backend-production.up.railway.app/admin/
- **Логин**: admin / admin123

## 🎙️ Транскрипция

### Локальная Whisper (бесплатная):
- **OpenAI Whisper** на сервере
- **Поддержка русского языка**
- **Работает офлайн**
- **Выбор модели** в интерфейсе

### Модели Whisper:
| Модель | Параметры | RAM | Качество | Рекомендация |
|--------|-----------|-----|----------|--------------|
| `tiny` | 39M | ~1GB | Базовое | Быстрые тесты |
| `base` | 74M | ~1GB | Хорошее | Повседневное использование |
| **`small`** | **244M** | **~2GB** | **Отличное** | **🎯 Рекомендуется для русского** |
| `medium` | 769M | ~5GB | Превосходное | Высокое качество |
| `large` | 1550M | ~10GB | Максимальное | Если есть ресурсы |

## 📡 API Endpoints

### Аутентификация
- `POST /api/auth/login` - Вход
- `POST /api/auth/register` - Регистрация
- `GET /api/auth/users` - Список пользователей (админ)

### Записи
- `POST /api/recordings/upload` - Загрузка аудио
- `GET /api/recordings` - Список записей пользователя
- `GET /api/recordings/admin` - Все записи (админ)
- `GET /api/recordings/stats` - Статистика записей
- `GET /api/recordings/:id` - Детали записи
- `GET /api/recordings/:id/audio` - Скачать аудио файл
- `POST /api/recordings/:id/transcribe` - Транскрипция (админ)
- `DELETE /api/recordings` - Массовое удаление (админ)

### Система
- `GET /api/recordings/system-check` - Диагностика Whisper/Python/FFmpeg

### Локации
- `GET /api/locations` - Список локаций
- `POST /api/locations` - Создать локацию (админ)
- `PUT /api/locations/:id` - Обновить локацию (админ)
- `DELETE /api/locations/:id` - Удалить локацию (админ)

## 🛠️ Технологии

- **Backend**: Node.js + Express
- **База данных**: PostgreSQL (Railway)
- **Аутентификация**: JWT
- **Транскрипция**: OpenAI Whisper (локально)
- **Деплой**: Railway с Nixpacks
- **Фронтенд**: Vanilla JS с современной тёмной темой

## 📋 Требования для Whisper

- **Python**: 3.8-3.11 (не 3.13!)
- **FFmpeg**: для обработки аудио
- **RAM**: 1-10GB (зависит от модели)
- **Зависимости**: openai-whisper, torch, torchaudio

## 🎉 Версии

- **v1.0-whisper** - Текущая стабильная версия с Whisper
- **v0.1** - Первоначальная версия с браузерной транскрипцией

## 🔗 Ссылки

- **GitHub**: https://github.com/kikanbig/contact-recorder-backend
- **Railway**: https://contact-recorder-backend-production.up.railway.app
- **Админ панель**: https://contact-recorder-backend-production.up.railway.app/admin/

---
**Версия**: 1.0  
**Дата**: Июнь 2025  
**Статус**: Стабильная рабочая версия ✅
