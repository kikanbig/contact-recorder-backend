# Настройка Railway

## Переменные окружения

Установите следующие переменные окружения в настройках Railway:

```env
NODE_ENV=production
PORT=8080
JWT_SECRET=your_secure_jwt_secret_here
DATABASE_URL=your_postgresql_url_here
```

## Настройки развертывания

1. Builder: Nixpacks
2. Start Command: `npm start`
3. Healthcheck Path: `/health`
4. Healthcheck Timeout: 300
5. Restart Policy: On Failure
6. Max Restart Retries: 10

## Проверка развертывания

После развертывания проверьте следующие эндпоинты:

1. `GET /` - Информация об API
2. `GET /health` - Статус сервера
3. `GET /db-test` - Тест подключения к PostgreSQL

## Доступ к админ-панели

1. URL: `https://your-railway-domain/admin`
2. Логин: `admin`
3. Пароль: `admin123`

## Мониторинг

1. Проверьте логи в разделе "Deployments"
2. Следите за метриками в разделе "Metrics"
3. При необходимости настройте алерты в разделе "Settings" 