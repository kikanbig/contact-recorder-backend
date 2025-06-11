# 🛠️ Трудности и Решения - Backend API

Документация всех проблем, с которыми мы столкнулись при разработке backend, и их решений.

## 🎯 Основная Проблема: GraphQL Multipart Интерпретация

### ❌ Проблема
React Native отправлял стандартные multipart/form-data запросы, но получал ошибку:
```
"Misordered multipart fields; files should follow 'map' (https://github.com/jaydenseric/graphql-multipart-request-spec)"
```

### 🔍 Причина
React Native/Expo автоматически применяет GraphQL multipart спецификацию к любым multipart запросам, ожидая структуру:
1. `operations` - JSON с GraphQL операцией
2. `map` - мапинг переменных к файлам  
3. Файлы в определенном порядке

### ✅ Решение Backend
Хотя проблема решалась на frontend, в backend мы улучшили обработку:

```javascript
// Поддержка обычных multipart запросов
router.post('/upload', authenticateToken, upload.single('audio'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        message: 'Аудио файл не предоставлен'
      });
    }
    
    // Обработка файла независимо от формата запроса
    const audioData = fs.readFileSync(req.file.path);
    // ...
  } catch (error) {
    console.error('Ошибка загрузки:', error);
  }
});
```

---

## 🔐 Проблема: Аутентификация на Production

### ❌ Проблема
Мобильное приложение не могло авторизоваться с тестовыми данными `продавец1/123456`.

### 🔍 Причина
На production Railway базе данных не было тестового пользователя, только:
- admin / admin123

### ✅ Решение
1. **Отладка через curl:**
```bash
# Тест рабочих учетных данных
curl -X POST https://contact-recorder-backend-production.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' 
```

2. **Улучшение логирования ошибок:**
```javascript
router.post('/login', async (req, res) => {
  console.log('🔐 Попытка входа:', req.body.username);
  
  const user = await db.getUserByUsername(username);
  if (!user) {
    console.log('❌ Пользователь не найден:', username);
    return res.status(401).json({
      success: false,
      message: 'Неверные учетные данные'
    });
  }
  // ...
});
```

---

## 🤖 Проблема: OpenAI API Квота

### ❌ Проблема
Транскрипция не работала с ошибкой:
```
"429 You exceeded your current quota, please check your plan and billing details"
```

### 🔍 Причина
OpenAI API имеет лимиты:
- Бесплатно: только $5 триальных кредитов
- Whisper: $0.006 за минуту аудио
- После исчерпания - платный план

### ✅ Решение
Создали браузерную альтернативу + улучшили обработку ошибок:

```javascript
// Понятные ошибки для пользователя
let userMessage = 'Ошибка выполнения транскрипции';

if (error.message.includes('429')) {
  userMessage = 'Исчерпан лимит OpenAI API. Пополните баланс аккаунта OpenAI для продолжения транскрипции.';
} else if (error.message.includes('quota')) {
  userMessage = 'Превышена квота OpenAI API. Пополните баланс или дождитесь обновления лимитов.';
} else if (error.message.includes('billing')) {
  userMessage = 'Проблема с оплатой OpenAI API. Проверьте биллинг в аккаунте OpenAI.';
}

res.status(500).json({
  success: false,
  message: userMessage,
  technical_error: error.message
});
```

**Браузерная транскрипция:**
```javascript
// Новый endpoint для сохранения браузерной транскрипции
router.post('/:id/transcribe-text', authenticateToken, requireAdmin, async (req, res) => {
  const { transcription } = req.body;
  
  const updatedRecording = await db.updateRecordingTranscription(req.params.id, transcription.trim());
  
  res.json({
    success: true,
    message: 'Транскрипция сохранена',
    transcription: transcription.trim(),
    transcribed_at: updatedRecording.transcribed_at
  });
});
```

---

## 🗄️ Проблема: PostgreSQL на Railway

### ❌ Проблема
Первоначально планировали SQLite, но для production нужна была PostgreSQL.

### ✅ Решение
Настроили PostgreSQL на Railway:

1. **Создание базы данных:**
```bash
# Railway автоматически предоставляет DATABASE_URL
DATABASE_URL=postgresql://postgres:password@monorail.proxy.rlwy.net:12345/railway
```

2. **Миграции схемы:**
```sql
-- Таблица пользователей
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(255),
  email VARCHAR(255),
  role VARCHAR(50) DEFAULT 'user',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица записей
CREATE TABLE recordings (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  location_id INTEGER REFERENCES locations(id),
  filename VARCHAR(255) NOT NULL,
  original_filename VARCHAR(255),
  file_size INTEGER,
  duration_seconds INTEGER,
  mime_type VARCHAR(100),
  audio_data BYTEA, -- Хранение аудио в базе
  transcription TEXT,
  transcribed_at TIMESTAMP,
  recording_date TIMESTAMP,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  status VARCHAR(50) DEFAULT 'uploaded'
);
```

3. **Подключение:**
```javascript
const { Pool } = require('pg');
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});
```

---

## 🌐 Проблема: CORS и Headers

### ❌ Проблема
Веб админ панель не могла подключиться к API из-за CORS.

### ✅ Решение
Настроили CORS middleware:

```javascript
const cors = require('cors');

app.use(cors({
  origin: ['https://contact-recorder-backend-production.up.railway.app', 'http://localhost:3000'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
```

---

## 📁 Проблема: Хранение Файлов

### ❌ Проблема
Railway не сохраняет файлы в файловой системе между деплоями.

### ✅ Решение
Храним аудио файлы в PostgreSQL как BYTEA:

```javascript
// Сохранение в базу
const audioData = fs.readFileSync(req.file.path);
const recording = await db.createRecording({
  // ...
  audio_data: audioData, // Сохраняем в БД
  // ...
});

// Удаляем временный файл
fs.unlink(req.file.path, (err) => {
  if (err) console.error('Ошибка удаления временного файла:', err);
});
```

---

## 🎙️ Решение: Браузерная Транскрипция

### ✅ Реализация
Добавили бесплатную альтернативу OpenAI через Web Speech Recognition:

```javascript
// Frontend (admin panel)
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();

recognition.continuous = true;
recognition.interimResults = false;
recognition.lang = 'ru-RU';

recognition.onresult = function(event) {
  let finalTranscription = '';
  for (let i = event.resultIndex; i < event.results.length; i++) {
    if (event.results[i].isFinal) {
      finalTranscription += event.results[i][0].transcript + ' ';
    }
  }
  
  // Отправляем результат на сервер
  fetch(`/api/recordings/${id}/transcribe-text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcription: finalTranscription.trim() })
  });
};
```

**Поддержка браузеров:**
- ✅ Chrome/Chromium (отлично)
- ✅ Edge (хорошо)
- ⚠️ Safari (частично)
- ❌ Firefox (нет поддержки)

---

## 🔒 Проблема: JWT Токены

### ❌ Проблема
Изначально использовали Basic Auth, что не подходило для production.

### ✅ Решение
Внедрили JWT аутентификацию:

```javascript
const jwt = require('jsonwebtoken');
const JWT_SECRET = process.env.JWT_SECRET || 'contact-recorder-secret-key';

// Генерация токена
const token = jwt.sign(
  { userId: user.id, username: user.username, role: user.role },
  JWT_SECRET,
  { expiresIn: '7d' }
);

// Middleware проверки
async function authenticateToken(req, res, next) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    const user = await db.getUserById(decoded.userId);
    req.user = user;
    next();
  } catch (error) {
    return res.status(401).json({ message: 'Недействительный токен' });
  }
}
```

---

## 📊 Проблема: Отчеты и Статистика

### ✅ Решение
Создали агрегированную статистику:

```javascript
router.get('/stats', authenticateToken, async (req, res) => {
  const stats = await db.getRecordingsStats();
  
  res.json({
    success: true,
    stats: {
      total_recordings: parseInt(stats.total_recordings),
      transcribed_recordings: parseInt(stats.transcribed_recordings),
      pending_transcriptions: parseInt(stats.total_recordings) - parseInt(stats.transcribed_recordings),
      total_duration_seconds: parseInt(stats.total_duration_seconds || 0)
    }
  });
});
```

---

## 🚀 Деплой на Railway

### ✅ Автоматический деплой
Настроили автоматический деплой через GitHub:

1. **Подключение репозитория** к Railway
2. **Переменные окружения:**
```env
NODE_ENV=production
JWT_SECRET=your-production-secret
OPENAI_API_KEY=sk-... (опционально)
DATABASE_URL=postgresql://... (автоматически)
PORT=3000 (автоматически)
```

3. **Railway автоматически:**
   - Запускает `npm install`
   - Выполняет `npm start`
   - Предоставляет HTTPS домен
   - Управляет PostgreSQL

---

## 💡 Ключевые Уроки

1. **Храните файлы в БД** - Railway не сохраняет файловую систему
2. **Логируйте все** - production отладка критически важна
3. **Graceful degradation** - предоставляйте альтернативы (браузерная транскрипция)
4. **Тестируйте API отдельно** - curl/Postman перед интеграцией с frontend
5. **JWT важнее Basic Auth** - для production обязательно
6. **OpenAI не бесплатен** - планируйте бюджет или альтернативы

---

## 🔗 Полезные Ссылки

- [Railway Documentation](https://docs.railway.app/)
- [PostgreSQL BYTEA Type](https://www.postgresql.org/docs/current/datatype-binary.html)
- [JWT Best Practices](https://auth0.com/blog/a-look-at-the-latest-draft-for-jwt-bcp/)
- [Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)
- [OpenAI Pricing](https://openai.com/pricing)
- [Express CORS](https://github.com/expressjs/cors) 