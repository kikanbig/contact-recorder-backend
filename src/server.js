require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');
// Используем SQLite для устранения проблем с Railway PostgreSQL
const { db, initDatabase } = process.env.USE_SQLITE ? 
  require('./models/database-sqlite') : 
  require('./models/database');

// Импорт роутов
const authRoutes = require('./routes/auth');
const locationsRoutes = require('./routes/locations');
const recordingRoutes = require('./routes/recordings');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Статические файлы для веб-панели
app.use('/admin', express.static(path.join(__dirname, '../public')));

// Подключение роутов
app.use('/api/auth', authRoutes);
app.use('/api/locations', locationsRoutes);
app.use('/api/recordings', recordingRoutes);

// Основной endpoint
app.get('/', (req, res) => {
  res.json({
    message: 'Contact Recorder API v3.0 - Администраторская панель готова!',
    version: '3.0.2-FORCED',
    features: [
      'Авторизация пользователей',
      'Управление локациями', 
      'Загрузка аудиозаписей',
      'Веб-панель администратора',
      'Транскрипция через OpenAI',
      'PostgreSQL база данных'
    ],
    status: 'active',
    admin_panel: '/admin',
    timestamp: new Date().toISOString()
  });
});

// Endpoint для проверки здоровья сервера
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development'
  });
});

// Endpoint для тестирования подключения к БД
app.get('/db-test', async (req, res) => {
  try {
    const result = await db.query('SELECT NOW() as current_time, version() as postgres_version');
    
    res.json({
      status: 'success',
      message: 'База данных подключена!',
      database_time: result.rows[0].current_time,
      postgres_version: result.rows[0].postgres_version.split(' ')[0] + ' ' + result.rows[0].postgres_version.split(' ')[1],
      database_url_exists: !!process.env.DATABASE_URL
    });
  } catch (error) {
    res.status(500).json({
      status: 'error',
      message: 'Ошибка подключения к базе данных',
      error: error.message,
      database_url_exists: !!process.env.DATABASE_URL
    });
  }
});

// Инициализация базы данных при запуске
async function startServer() {
  try {
    console.log('🔄 Инициализация базы данных...');
    await initDatabase();
    
    // Запуск сервера
    app.listen(PORT, '0.0.0.0', () => {
      console.log(`🚀 Server running on port ${PORT}`);
      console.log(`📊 DATABASE_URL status: ${process.env.DATABASE_URL ? '✅ configured' : '❌ not configured'}`);
      
      console.log('\n📋 Available endpoints:');
      console.log('  GET  / - API информация');
      console.log('  GET  /health - Статус сервера');
      console.log('  GET  /db-test - Тест базы данных');
      console.log('  GET  /admin - Веб-панель администратора');
      console.log('  POST /api/auth/login - Авторизация');
      console.log('  GET  /api/auth/me - Профиль пользователя');
      console.log('  GET  /api/locations - Список локаций');
      console.log('  POST /api/recordings/upload - Загрузка записи');
      console.log('  GET  /api/recordings - Список записей');
      console.log('  GET  /api/recordings/admin - Все записи для админа');
      console.log('  GET  /api/recordings/stats - Статистика записей');
      console.log('  POST /api/recordings/:id/transcribe - Транскрипция записи');
      console.log('  GET  /api/recordings/:id/transcription - Получить транскрипцию');
      
      console.log('\n🔐 Админский доступ:');
      console.log('  Логин: admin');
      console.log('  Пароль: admin123');
    });
    
  } catch (error) {
    console.error('❌ Ошибка запуска сервера:', error);
    process.exit(1);
  }
}

// Запуск сервера
startServer();
