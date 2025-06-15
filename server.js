const express = require('express');
const multer = require('multer');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Статические файлы
app.use('/admin', express.static(path.join(__dirname, 'admin')));

// Настройка multer для загрузки файлов в персистентную директорию
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    ensureDirectories();
    cb(null, UPLOADS_DIR);
  },
  filename: function (req, file, cb) {
    const timestamp = Date.now();
    const originalName = Buffer.from(file.originalname, 'latin1').toString('utf8');
    cb(null, `${timestamp}_${originalName}`);
  }
});

const upload = multer({ 
  storage: storage,
  limits: {
    fileSize: 100 * 1024 * 1024 // 100MB
  }
});

// Персистентное хранилище данных
const DATA_DIR = process.env.RAILWAY_VOLUME_MOUNT_PATH || '/app/data';
const DB_FILE = path.join(DATA_DIR, 'recordings.json');
const UPLOADS_DIR = path.join(DATA_DIR, 'uploads');

// Создаем директории если их нет
function ensureDirectories() {
  try {
    if (!fs.existsSync(DATA_DIR)) {
      fs.mkdirSync(DATA_DIR, { recursive: true });
      console.log('📁 Создана директория данных:', DATA_DIR);
    }
    if (!fs.existsSync(UPLOADS_DIR)) {
      fs.mkdirSync(UPLOADS_DIR, { recursive: true });
      console.log('📁 Создана директория загрузок:', UPLOADS_DIR);
    }
  } catch (error) {
    console.error('❌ Ошибка создания директорий:', error);
  }
}

// Функции для работы с базой данных
function loadDatabase() {
  try {
    ensureDirectories();
    if (fs.existsSync(DB_FILE)) {
      const data = fs.readFileSync(DB_FILE, 'utf8');
      const records = JSON.parse(data);
      console.log(`📊 Загружено записей из базы: ${records.length}`);
      return records;
    } else {
      console.log('📊 База данных не найдена, создаем новую');
    }
  } catch (error) {
    console.error('❌ Ошибка загрузки базы данных:', error);
  }
  return [];
}

function saveDatabase(records) {
  try {
    ensureDirectories();
    fs.writeFileSync(DB_FILE, JSON.stringify(records, null, 2));
    console.log(`💾 Сохранено записей в базу: ${records.length}`);
    return true;
  } catch (error) {
    console.error('❌ Ошибка сохранения базы данных:', error);
    return false;
  }
}

// Главная страница
app.get('/', (req, res) => {
  res.send(`
    <html>
      <head>
        <title>21 Век - Система транскрипции v3.2.1</title>
        <style>
          body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
            padding: 50px;
            margin: 0;
          }
          .container { max-width: 800px; margin: 0 auto; }
          h1 { font-size: 3rem; margin-bottom: 20px; }
          .subtitle { font-size: 1.2rem; opacity: 0.9; margin-bottom: 40px; }
          .features { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; 
            margin: 40px 0; 
          }
          .feature { 
            background: rgba(255,255,255,0.1); 
            padding: 20px; 
            border-radius: 10px; 
            backdrop-filter: blur(10px);
          }
          .btn {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 25px;
            margin: 10px;
            transition: all 0.3s ease;
            border: 2px solid rgba(255,255,255,0.3);
          }
          .btn:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
          }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>🎤 21 Век</h1>
          <div class="subtitle">Система транскрипции аудио с диаризацией v3.2.1</div>
          
          <div class="features">
            <div class="feature">
              <h3>📱 Мобильное приложение</h3>
              <p>Загрузка записей с мобильного устройства</p>
            </div>
            <div class="feature">
              <h3>🎯 Диаризация спикеров</h3>
              <p>Автоматическое разделение по говорящим через SpeechBrain</p>
            </div>
            <div class="feature">
              <h3>⚡ Быстрая транскрипция</h3>
              <p>Faster-Whisper для ускоренной обработки</p>
            </div>
            <div class="feature">
              <h3>🎛️ Управление по требованию</h3>
              <p>Транскрипция только при необходимости</p>
            </div>
          </div>
          
          <div>
            <a href="/admin" class="btn">🔧 Админ панель</a>
            <a href="/health" class="btn">💚 Проверка системы</a>
          </div>
          
          <div style="margin-top: 40px; opacity: 0.7; font-size: 0.9rem;">
            <p>API эндпоинты:</p>
            <p>POST /api/recordings/upload - Загрузка записи</p>
            <p>POST /api/records/:id/transcribe - Транскрипция записи</p>
            <p>GET /api/records - Список записей</p>
          </div>
        </div>
      </body>
    </html>
  `);
});

// Проверка здоровья системы
app.get('/health', async (req, res) => {
  const records = loadDatabase();
  const health = {
    status: 'OK',
    timestamp: new Date().toISOString(),
    version: '3.2.1',
    storage: {
      type: 'Railway Volume',
      data_dir: DATA_DIR,
      db_file: DB_FILE,
      uploads_dir: UPLOADS_DIR,
      records_count: records.length,
      db_exists: fs.existsSync(DB_FILE),
      uploads_exists: fs.existsSync(UPLOADS_DIR)
    },
    services: {
      database: 'OK',
      python: 'Checking...',
      whisper: 'Checking...',
      speechbrain: 'Checking...'
    }
  };

  // Проверка Python
  try {
    await runCommand('python3', ['--version']);
    health.services.python = 'OK';
  } catch (error) {
    health.services.python = 'ERROR: ' + error.message;
    health.status = 'DEGRADED';
  }

  // Проверка Whisper
  try {
    await runCommand('python3', ['-c', 'import faster_whisper; print("OK")']);
    health.services.whisper = 'OK';
  } catch (error) {
    health.services.whisper = 'ERROR: ' + error.message;
    health.status = 'DEGRADED';
  }

  // Проверка SpeechBrain
  try {
    await runCommand('python3', ['-c', 'import speechbrain; print("OK")']);
    health.services.speechbrain = 'OK';
  } catch (error) {
    health.services.speechbrain = 'ERROR: ' + error.message;
    health.status = 'DEGRADED';
  }

  res.json(health);
});

// API: Загрузка записи (БЕЗ автоматической транскрипции)
app.post('/api/recordings/upload', upload.single('audio'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        message: 'Аудио файл не предоставлен'
      });
    }

    const { 
      location_id, 
      duration_seconds,
      recording_date,
      metadata
    } = req.body;

    console.log('📁 Загружаем аудио файл:', req.file.originalname);
    console.log('📊 Размер файла:', req.file.size, 'байт');
    console.log('📍 Локация:', location_id);

    // Создаем запись
    const records = loadDatabase();
    const newRecord = {
      id: Date.now().toString(),
      filename: req.file.originalname,
      file_path: req.file.path,
      file_size: req.file.size,
      duration_seconds: duration_seconds ? parseInt(duration_seconds) : null,
      location_id: location_id || null,
      recording_date: recording_date || new Date().toISOString(),
      created_at: new Date().toISOString(),
      source: 'mobile_app',
      metadata: metadata ? JSON.parse(metadata) : null,
      // НЕ добавляем транскрипцию автоматически
      text: null,
      segments: null,
      speaker_count: null,
      transcribed_at: null
    };

    records.push(newRecord);
    saveDatabase(records);

    console.log('✅ Запись сохранена с ID:', newRecord.id);

    res.json({
      success: true,
      message: 'Аудио файл успешно загружен',
      recording: {
        id: newRecord.id,
        filename: newRecord.filename,
        duration_seconds: newRecord.duration_seconds,
        file_size: newRecord.file_size,
        created_at: newRecord.created_at,
        status: 'uploaded'
      }
    });

  } catch (error) {
    console.error('❌ Ошибка загрузки:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка загрузки аудио файла: ' + error.message
    });
  }
});

// API: Получить все записи
app.get('/api/records', (req, res) => {
  try {
    const records = loadDatabase();
    res.json(records);
  } catch (error) {
    console.error('❌ Ошибка получения записей:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка получения записей'
    });
  }
});

// API: Транскрипция записи по требованию
app.post('/api/records/:id/transcribe', async (req, res) => {
  try {
    const recordId = req.params.id;
    const { model = 'small' } = req.body;

    console.log(`🎤 Начинаем транскрипцию записи ${recordId} с моделью ${model}`);

    const records = loadDatabase();
    const record = records.find(r => r.id === recordId);

    if (!record) {
      return res.status(404).json({
        success: false,
        message: 'Запись не найдена'
      });
    }

    if (record.text) {
      return res.json({
        success: true,
        message: 'Запись уже транскрибирована',
        text: record.text,
        segments: record.segments,
        speaker_count: record.speaker_count,
        transcribed_at: record.transcribed_at
      });
    }

    if (!fs.existsSync(record.file_path)) {
      return res.status(400).json({
        success: false,
        message: 'Аудио файл не найден на сервере'
      });
    }

    // Выполняем транскрипцию с диаризацией
    console.log('🔄 Запускаем транскрипцию с диаризацией...');
    const result = await transcribeWithDiarization(record.file_path, model);

    // Обновляем запись в базе данных
    record.text = result.text;
    record.segments = result.segments;
    record.speaker_count = result.speaker_count;
    record.transcribed_at = new Date().toISOString();

    saveDatabase(records);

    console.log('✅ Транскрипция завершена для записи:', recordId);

    res.json({
      success: true,
      message: 'Транскрипция завершена успешно',
      text: result.text,
      segments: result.segments,
      speaker_count: result.speaker_count,
      transcribed_at: record.transcribed_at
    });

  } catch (error) {
    console.error('❌ Ошибка транскрипции:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка транскрипции: ' + error.message
    });
  }
});

// API: Удаление записи
app.delete('/api/records/:id', (req, res) => {
  try {
    const recordId = req.params.id;
    const records = loadDatabase();
    const recordIndex = records.findIndex(r => r.id === recordId);

    if (recordIndex === -1) {
      return res.status(404).json({
        success: false,
        message: 'Запись не найдена'
      });
    }

    const record = records[recordIndex];

    // Удаляем файл с диска
    if (fs.existsSync(record.file_path)) {
      fs.unlinkSync(record.file_path);
    }

    // Удаляем из базы данных
    records.splice(recordIndex, 1);
    saveDatabase(records);

    console.log('🗑️ Запись удалена:', recordId);

    res.json({
      success: true,
      message: 'Запись успешно удалена'
    });

  } catch (error) {
    console.error('❌ Ошибка удаления записи:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка удаления записи'
    });
  }
});

// API: Массовое удаление записей
app.post('/api/records/bulk-delete', (req, res) => {
  try {
    const { ids } = req.body;

    if (!Array.isArray(ids) || ids.length === 0) {
      return res.status(400).json({
        success: false,
        message: 'Не указаны ID записей для удаления'
      });
    }

    const records = loadDatabase();
    let deletedCount = 0;

    // Удаляем записи
    for (let i = records.length - 1; i >= 0; i--) {
      if (ids.includes(records[i].id)) {
        const record = records[i];
        
        // Удаляем файл с диска
        if (fs.existsSync(record.file_path)) {
          fs.unlinkSync(record.file_path);
        }
        
        records.splice(i, 1);
        deletedCount++;
      }
    }

    saveDatabase(records);

    console.log(`🗑️ Массово удалено записей: ${deletedCount}`);

    res.json({
      success: true,
      message: `Успешно удалено записей: ${deletedCount}`,
      deleted_count: deletedCount
    });

  } catch (error) {
    console.error('❌ Ошибка массового удаления:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка массового удаления записей'
    });
  }
});

// Функция транскрипции с диаризацией
async function transcribeWithDiarization(audioFilePath, model = 'small') {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(__dirname, 'transcription_service_speechbrain.py');
    
    console.log(`🔍 Запуск транскрипции: ${scriptPath}`);
    console.log(`📁 Аудио файл: ${audioFilePath}`);
    console.log(`🤖 Модель: ${model}`);
    
    if (!fs.existsSync(scriptPath)) {
      reject(new Error(`Python скрипт не найден: ${scriptPath}`));
      return;
    }
    
    if (!fs.existsSync(audioFilePath)) {
      reject(new Error(`Аудио файл не найден: ${audioFilePath}`));
      return;
    }
    
    const pythonProcess = spawn('python3', [
      scriptPath,
      audioFilePath,
      'ru',
      model
    ], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONUNBUFFERED: '1' }
    });

    let stdout = '';
    let stderr = '';

    pythonProcess.stdout.on('data', (data) => {
      const output = data.toString();
      stdout += output;
      console.log('🐍 Python stdout:', output.trim());
    });

    pythonProcess.stderr.on('data', (data) => {
      const output = data.toString();
      stderr += output;
      console.log('🐍 Python stderr:', output.trim());
    });

    // Таймаут 20 минут
    const timeout = setTimeout(() => {
      pythonProcess.kill('SIGTERM');
      reject(new Error('Превышено время ожидания транскрипции (20 минут)'));
    }, 20 * 60 * 1000);

    pythonProcess.on('close', (code) => {
      clearTimeout(timeout);
      
      console.log(`🏁 Python процесс завершён с кодом: ${code}`);
      
      if (code !== 0) {
        console.error('❌ Ошибка Python процесса:', stderr);
        reject(new Error(`Python процесс завершился с кодом ${code}: ${stderr}`));
        return;
      }

      try {
        // Парсим результат
        const lines = stdout.trim().split('\n');
        const lastLine = lines[lines.length - 1];
        
        if (lastLine.startsWith('{')) {
          const result = JSON.parse(lastLine);
          resolve(result);
        } else {
          // Fallback для простого текста
          resolve({
            text: stdout.trim(),
            segments: [],
            speaker_count: 1
          });
        }
      } catch (parseError) {
        console.error('❌ Ошибка парсинга результата:', parseError);
        reject(new Error('Ошибка парсинга результата транскрипции'));
      }
    });

    pythonProcess.on('error', (error) => {
      clearTimeout(timeout);
      console.error('❌ Ошибка запуска Python процесса:', error);
      reject(new Error(`Ошибка запуска Python: ${error.message}`));
    });
  });
}

// Вспомогательная функция для выполнения команд
function runCommand(command, args) {
  return new Promise((resolve, reject) => {
    const process = spawn(command, args);
    let output = '';
    let error = '';

    process.stdout.on('data', (data) => {
      output += data.toString();
    });

    process.stderr.on('data', (data) => {
      error += data.toString();
    });

    process.on('close', (code) => {
      if (code === 0) {
        resolve(output.trim());
      } else {
        reject(new Error(error.trim() || `Command failed with code ${code}`));
      }
    });

    process.on('error', (err) => {
      reject(err);
    });
  });
}

// Запуск сервера
app.listen(PORT, '0.0.0.0', () => {
  const records = loadDatabase();
  console.log(`
🚀 Сервер запущен на порту ${PORT}

📋 Доступные эндпоинты:
   🏠 Главная: http://0.0.0.0:${PORT}/
   🔧 Админ: http://0.0.0.0:${PORT}/admin/
   💚 Здоровье: http://0.0.0.0:${PORT}/health

📱 API для мобильного приложения:
   📤 Загрузка: POST http://0.0.0.0:${PORT}/api/recordings/upload
   📋 Записи: GET http://0.0.0.0:${PORT}/api/records
   🎤 Транскрипция: POST http://0.0.0.0:${PORT}/api/records/:id/transcribe

💾 ПЕРСИСТЕНТНОЕ ХРАНИЛИЩЕ:
   📁 Директория данных: ${DATA_DIR}
   📊 База данных: ${DB_FILE}
   📂 Загрузки: ${UPLOADS_DIR}
   📈 Записей в базе: ${records.length}
   ✅ Данные сохраняются при редеплое!

🎯 Особенности v3.2.1:
   ✅ Загрузка записей БЕЗ автоматической транскрипции
   ✅ Транскрипция по требованию через админ панель
   ✅ Диаризация через SpeechBrain + pyannote.audio
   ✅ Современный черный дизайн админки
   ✅ Массовые операции с записями
   ✅ Персистентное хранилище данных (Railway Volume)
  `);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('🛑 Получен сигнал SIGTERM, завершаем сервер...');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('🛑 Получен сигнал SIGINT, завершаем сервер...');
  process.exit(0);
}); 