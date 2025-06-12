const express = require('express');
const jwt = require('jsonwebtoken');
const fs = require('fs');
const path = require('path');
const multer = require('multer');
const { OpenAI } = require('openai');
const { db } = require('../models/database');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'contact-recorder-secret-key';

// OpenAI клиент для транскрипции
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const openai = OPENAI_API_KEY ? new OpenAI({ apiKey: OPENAI_API_KEY }) : null;

// Настройка multer для загрузки файлов
const upload = multer({
  dest: 'uploads/',
  limits: { fileSize: 50 * 1024 * 1024 }, // 50MB
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['audio/mpeg', 'audio/mp4', 'audio/m4a', 'audio/wav', 'audio/webm', 'audio/aac'];
    if (allowedTypes.includes(file.mimetype) || file.originalname.match(/\.(m4a|mp3|wav|aac|webm)$/i)) {
      cb(null, true);
    } else {
      cb(new Error('Неподдерживаемый формат файла'), false);
    }
  }
});

// Middleware для проверки токена
async function authenticateToken(req, res, next) {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    
    if (!token) {
      return res.status(401).json({
        success: false,
        message: 'Токен не предоставлен'
      });
    }

    const decoded = jwt.verify(token, JWT_SECRET);
    const user = await db.getUserById(decoded.userId);
    
    if (!user) {
      return res.status(401).json({
        success: false,
        message: 'Пользователь не найден'
      });
    }

    req.user = user;
    next();
  } catch (error) {
    res.status(401).json({
      success: false,
      message: 'Недействительный токен'
    });
  }
}

// Middleware для проверки прав администратора
function requireAdmin(req, res, next) {
  if (req.user.role !== 'admin') {
    return res.status(403).json({
      success: false,
      message: 'Требуются права администратора'
    });
  }
  next();
}

// POST /api/recordings/upload - Загрузка аудио файла (для мобильного приложения)
router.post('/upload', authenticateToken, upload.single('audio'), async (req, res) => {
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
    console.log('👤 Пользователь:', req.user.username);
    console.log('📍 Локация:', location_id);

    // Читаем файл в base64 для хранения в PostgreSQL
    const audioData = fs.readFileSync(req.file.path);

    // Создаем запись в базе данных
    const recording = await db.createRecording({
      user_id: req.user.id,
      location_id: location_id ? parseInt(location_id) : null,
      filename: `${Date.now()}_${req.file.originalname}`,
      original_filename: req.file.originalname,
      file_path: req.file.path,
      file_size: req.file.size,
      duration_seconds: duration_seconds ? parseInt(duration_seconds) : null,
      mime_type: req.file.mimetype,
      audio_data: audioData,
      recording_date: recording_date ? new Date(recording_date) : new Date(),
      metadata: metadata ? JSON.parse(metadata) : null
    });

    // Удаляем временный файл
    fs.unlink(req.file.path, (err) => {
      if (err) console.error('Ошибка удаления временного файла:', err);
    });

    res.json({
      success: true,
      message: 'Аудио файл успешно загружен',
      recording: {
        id: recording.id,
        filename: recording.filename,
        duration_seconds: recording.duration_seconds,
        file_size: recording.file_size,
        uploaded_at: recording.uploaded_at,
        status: recording.status
      }
    });

  } catch (error) {
    console.error('Ошибка загрузки аудио:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка загрузки аудио файла'
    });
  }
});

// GET /api/recordings - Получить записи текущего пользователя
router.get('/', authenticateToken, async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 50;
    const offset = parseInt(req.query.offset) || 0;
    
    const recordings = await db.getRecordingsByUser(req.user.id, limit, offset);
    
    res.json({
      success: true,
      recordings: recordings.map(recording => ({
        id: recording.id,
        filename: recording.original_filename,
        duration_seconds: recording.duration_seconds,
        file_size: recording.file_size,
        location_name: recording.location_name,
        recording_date: recording.recording_date,
        uploaded_at: recording.uploaded_at,
        status: recording.status,
        has_transcription: !!recording.transcription,
        transcribed_at: recording.transcribed_at
      })),
      pagination: {
        limit,
        offset,
        has_more: recordings.length === limit
      }
    });

  } catch (error) {
    console.error('Ошибка получения записей:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка получения записей'
    });
  }
});

// GET /api/recordings/admin - Получить все записи (только для администраторов)
router.get('/admin', authenticateToken, requireAdmin, async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 100;
    const offset = parseInt(req.query.offset) || 0;
    
    const recordings = await db.getAllRecordings(limit, offset);
    
    res.json({
      success: true,
      recordings: recordings.map(recording => ({
        id: recording.id,
        filename: recording.original_filename,
        duration_seconds: recording.duration_seconds,
        file_size: recording.file_size,
        user: {
          id: recording.user_id,
          username: recording.username,
          full_name: recording.full_name
        },
        location: {
          id: recording.location_id,
          name: recording.location_name,
          address: recording.location_address
        },
        recording_date: recording.recording_date,
        uploaded_at: recording.uploaded_at,
        status: recording.status,
        has_transcription: !!recording.transcription,
        transcribed_at: recording.transcribed_at,
        transcription_preview: recording.transcription ? recording.transcription.substring(0, 100) + '...' : null
      })),
      pagination: {
        limit,
        offset,
        has_more: recordings.length === limit
      }
    });

  } catch (error) {
    console.error('Ошибка получения записей для админа:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка получения записей'
    });
  }
});

// GET /api/recordings/:id - Получить конкретную запись
router.get('/:id', authenticateToken, async (req, res) => {
  try {
    const recording = await db.getRecordingById(req.params.id);
    
    if (!recording) {
      return res.status(404).json({
        success: false,
        message: 'Запись не найдена'
      });
    }

    // Проверяем права доступа
    if (req.user.role !== 'admin' && recording.user_id !== req.user.id) {
      return res.status(403).json({
        success: false,
        message: 'Доступ запрещен'
      });
    }

    res.json({
      success: true,
      recording: {
        id: recording.id,
        filename: recording.original_filename,
        duration_seconds: recording.duration_seconds,
        file_size: recording.file_size,
        user: {
          id: recording.user_id,
          username: recording.username,
          full_name: recording.full_name
        },
        location: {
          id: recording.location_id,
          name: recording.location_name,
          address: recording.location_address
        },
        recording_date: recording.recording_date,
        uploaded_at: recording.uploaded_at,
        status: recording.status,
        transcription: recording.transcription,
        transcribed_at: recording.transcribed_at,
        metadata: recording.metadata
      }
    });

  } catch (error) {
    console.error('Ошибка получения записи:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка получения записи'
    });
  }
});

// GET /api/recordings/:id/audio - Получить аудио файл
router.get('/:id/audio', authenticateToken, async (req, res) => {
  try {
    const recording = await db.getRecordingById(req.params.id);
    
    if (!recording) {
      return res.status(404).json({
        success: false,
        message: 'Запись не найдена'
      });
    }

    // Проверяем права доступа
    if (req.user.role !== 'admin' && recording.user_id !== req.user.id) {
      return res.status(403).json({
        success: false,
        message: 'Доступ запрещен'
      });
    }

    if (!recording.audio_data) {
      return res.status(404).json({
        success: false,
        message: 'Аудио данные не найдены'
      });
    }

    res.set({
      'Content-Type': recording.mime_type || 'audio/mpeg',
      'Content-Length': recording.audio_data.length,
      'Content-Disposition': `attachment; filename="${recording.original_filename}"`
    });

    res.send(recording.audio_data);

  } catch (error) {
    console.error('Ошибка получения аудио:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка получения аудио файла'
    });
  }
});

// POST /api/recordings/:id/transcribe - Транскрипция записи (только для администраторов)
router.post('/:id/transcribe', authenticateToken, requireAdmin, async (req, res) => {
  try {
    const recording = await db.getRecordingById(req.params.id);
    
    if (!recording) {
      return res.status(404).json({
        success: false,
        message: 'Запись не найдена'
      });
    }

    if (recording.transcription) {
      return res.json({
        success: true,
        message: 'Запись уже транскрибирована',
        transcription: recording.transcription,
        transcribed_at: recording.transcribed_at
      });
    }

    if (!recording.audio_data) {
      return res.status(400).json({
        success: false,
        message: 'Аудио данные не найдены'
      });
    }

    console.log('📝 Начинаем локальную транскрипцию записи ID:', req.params.id);

    // Создаем временный файл для Whisper
    const tempFilePath = path.join('uploads', `temp_${recording.id}_${Date.now()}.m4a`);
    fs.writeFileSync(tempFilePath, recording.audio_data);

    try {
          // Выполняем транскрипцию через локальный Whisper
    const transcription = await transcribeWithLocalWhisper(tempFilePath);

      console.log('✅ Локальная транскрипция завершена для записи ID:', req.params.id);

      // Обновляем запись в базе данных
      const updatedRecording = await db.updateRecordingTranscription(req.params.id, transcription);

      // Удаляем временный файл
      fs.unlink(tempFilePath, (err) => {
        if (err) console.error('Ошибка удаления временного файла:', err);
      });

      res.json({
        success: true,
        message: 'Локальная транскрипция завершена',
        transcription: transcription,
        transcribed_at: updatedRecording.transcribed_at
      });

    } catch (transcriptionError) {
      // Удаляем временный файл в случае ошибки
      fs.unlink(tempFilePath, (err) => {
        if (err) console.error('Ошибка удаления временного файла:', err);
      });
      throw transcriptionError;
    }

  } catch (error) {
    console.error('Ошибка локальной транскрипции:', error);
    
    // Определяем тип ошибки для пользователя
    let userMessage = 'Ошибка выполнения локальной транскрипции';
    
    if (error.message.includes('python')) {
      userMessage = 'Python не найден на сервере. Обратитесь к администратору.';
    } else if (error.message.includes('whisper')) {
      userMessage = 'Whisper не установлен. Обратитесь к администратору.';
    } else if (error.message.includes('ffmpeg')) {
      userMessage = 'FFmpeg не найден на сервере. Обратитесь к администратору.';
    } else if (error.message.includes('memory') || error.message.includes('CUDA')) {
      userMessage = 'Недостаточно ресурсов сервера для транскрипции. Попробуйте позже.';
    }
    
    res.status(500).json({
      success: false,
      message: userMessage,
      technical_error: error.message
    });
  }
});

// Функция для вызова локального Whisper
async function transcribeWithLocalWhisper(audioFilePath, language = 'ru', modelSize = 'base') {
  return new Promise((resolve, reject) => {
    const { spawn } = require('child_process');
    
    const scriptPath = path.join(__dirname, '..', '..', 'transcription_service.py');
    console.log(`🔍 Запуск транскрипции: ${scriptPath}`);
    console.log(`📁 Аудио файл: ${audioFilePath}`);
    console.log(`🌍 Язык: ${language}, Модель: ${modelSize}`);
    
    // Проверяем существование файлов
    if (!fs.existsSync(scriptPath)) {
      reject(new Error(`Python скрипт не найден: ${scriptPath}`));
      return;
    }
    
    if (!fs.existsSync(audioFilePath)) {
      reject(new Error(`Аудио файл не найден: ${audioFilePath}`));
      return;
    }
    
    // Вызываем Python скрипт для транскрипции
    const pythonProcess = spawn('python3', [
      scriptPath,
      audioFilePath,
      language,
      modelSize
    ], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONUNBUFFERED: '1' }
    });

    let stdout = '';
    let stderr = '';

    pythonProcess.stdout.on('data', (data) => {
      const output = data.toString();
      stdout += output;
      console.log('🐍 Python stdout:', output);
    });

    pythonProcess.stderr.on('data', (data) => {
      const output = data.toString();
      stderr += output;
      console.log('🐍 Python stderr:', output);
    });

    pythonProcess.on('close', (code) => {
      console.log(`🏁 Python процесс завершён с кодом: ${code}`);
      console.log(`📤 Полный stdout: ${stdout}`);
      console.log(`📤 Полный stderr: ${stderr}`);
      
      if (code !== 0) {
        console.error('❌ Ошибка Python процесса:', stderr);
        
        // Детальный анализ ошибок
        let errorMessage = `Python процесс завершился с кодом ${code}`;
        
        if (stderr.includes('ModuleNotFoundError: No module named \'whisper\'')) {
          errorMessage = 'Модуль Whisper не установлен на сервере';
        } else if (stderr.includes('ModuleNotFoundError')) {
          errorMessage = 'Отсутствуют Python зависимости: ' + stderr;
        } else if (stderr.includes('CUDA')) {
          errorMessage = 'Проблема с CUDA/GPU: ' + stderr;
        } else if (stderr.includes('ffmpeg')) {
          errorMessage = 'FFmpeg не найден или некорректен: ' + stderr;
        } else if (stderr.includes('OutOfMemoryError') || stderr.includes('memory')) {
          errorMessage = 'Недостаточно памяти для обработки: ' + stderr;
        } else {
          errorMessage += ': ' + stderr;
        }
        
        reject(new Error(errorMessage));
        return;
      }

      try {
        // Парсим JSON ответ от Python скрипта
        const jsonOutput = stdout.trim();
        console.log(`📋 Попытка парсинга JSON: ${jsonOutput}`);
        
        const result = JSON.parse(jsonOutput);
        
        if (result.success) {
          console.log(`✅ Транскрипция успешна: ${result.text.substring(0, 100)}...`);
          resolve(result.text);
        } else {
          console.error(`❌ Whisper вернул ошибку: ${result.error}`);
          reject(new Error(result.error || 'Неизвестная ошибка транскрипции'));
        }
      } catch (parseError) {
        console.error('❌ Ошибка парсинга JSON ответа:', parseError);
        console.error('🔍 Сырой вывод Python:', stdout);
        
        // Если JSON не парсится, возможно это не JSON вывод
        if (stdout.trim()) {
          reject(new Error(`Некорректный ответ от Whisper. Ожидался JSON, получено: ${stdout.substring(0, 200)}`));
        } else {
          reject(new Error(`Python скрипт не вернул данных. Stderr: ${stderr}`));
        }
      }
    });

    pythonProcess.on('error', (error) => {
      console.error('❌ Ошибка запуска Python процесса:', error);
      
      if (error.code === 'ENOENT') {
        reject(new Error('Python3 не найден на сервере. Проверьте установку Python.'));
      } else {
        reject(new Error(`Ошибка запуска Python: ${error.message}`));
      }
    });
    
    // Таймаут для очень долгих операций
    setTimeout(() => {
      if (!pythonProcess.killed) {
        pythonProcess.kill('SIGTERM');
        reject(new Error('Транскрипция прервана по таймауту (5 минут)'));
      }
    }, 5 * 60 * 1000); // 5 минут
  });
}

// POST /api/recordings/:id/transcribe-text - Сохранение готовой транскрипции (только для администраторов)
router.post('/:id/transcribe-text', authenticateToken, requireAdmin, async (req, res) => {
  try {
    const { transcription } = req.body;

    if (!transcription || typeof transcription !== 'string') {
      return res.status(400).json({
        success: false,
        message: 'Текст транскрипции не предоставлен'
      });
    }

    const recording = await db.getRecordingById(req.params.id);
    
    if (!recording) {
      return res.status(404).json({
        success: false,
        message: 'Запись не найдена'
      });
    }

    console.log('💾 Сохраняем браузерную транскрипцию для записи ID:', req.params.id);

    // Обновляем запись в базе данных
    const updatedRecording = await db.updateRecordingTranscription(req.params.id, transcription.trim());

    res.json({
      success: true,
      message: 'Транскрипция сохранена',
      transcription: transcription.trim(),
      transcribed_at: updatedRecording.transcribed_at
    });

  } catch (error) {
    console.error('Ошибка сохранения транскрипции:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка сохранения транскрипции'
    });
  }
});

// GET /api/recordings/stats - Статистика записей
router.get('/stats', authenticateToken, async (req, res) => {
  try {
    const stats = await db.getRecordingsStats();
    
    // Дополнительная статистика для администраторов
    let userStats = null;
    if (req.user.role === 'admin') {
      userStats = stats;
    } else {
      // Статистика только для текущего пользователя
      const userRecordings = await db.getRecordingsByUser(req.user.id, 1000, 0);
      userStats = {
        total_recordings: userRecordings.length,
        transcribed_recordings: userRecordings.filter(r => r.transcription).length,
        total_duration_seconds: userRecordings.reduce((sum, r) => sum + (r.duration_seconds || 0), 0),
        avg_duration_seconds: userRecordings.length > 0 ? 
          userRecordings.reduce((sum, r) => sum + (r.duration_seconds || 0), 0) / userRecordings.length : 0
      };
    }

    res.json({
      success: true,
      stats: {
        total_recordings: parseInt(userStats.total_recordings),
        transcribed_recordings: parseInt(userStats.transcribed_recordings),
        pending_transcriptions: parseInt(userStats.total_recordings) - parseInt(userStats.transcribed_recordings),
        unique_users: userStats.unique_users ? parseInt(userStats.unique_users) : null,
        unique_locations: userStats.unique_locations ? parseInt(userStats.unique_locations) : null,
        total_duration_seconds: parseInt(userStats.total_duration_seconds || 0),
        avg_duration_seconds: Math.round(parseFloat(userStats.avg_duration_seconds || 0))
      }
    });

  } catch (error) {
    console.error('Ошибка получения статистики:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка получения статистики'
    });
  }
});

// GET /api/recordings/system-check - Проверка состояния системы (Python, Whisper)
router.get('/system-check', authenticateToken, requireAdmin, async (req, res) => {
  const diagnostics = {
    timestamp: new Date().toISOString(),
    python: { available: false, version: null, error: null },
    whisper: { available: false, version: null, error: null },
    ffmpeg: { available: false, version: null, error: null },
    transcription_script: { exists: false, path: null, error: null }
  };

  try {
    // Проверяем Python
    try {
      const pythonCheck = await runCommand('python3', ['--version']);
      diagnostics.python.available = true;
      diagnostics.python.version = pythonCheck.stdout.trim();
    } catch (error) {
      diagnostics.python.error = error.message;
    }

    // Проверяем FFmpeg
    try {
      const ffmpegCheck = await runCommand('ffmpeg', ['-version']);
      diagnostics.ffmpeg.available = true;
      diagnostics.ffmpeg.version = ffmpegCheck.stdout.split('\n')[0];
    } catch (error) {
      diagnostics.ffmpeg.error = error.message;
    }

    // Проверяем Whisper
    try {
      const whisperCheck = await runCommand('python3', ['-c', 'import whisper; print(whisper.__version__)']);
      diagnostics.whisper.available = true;
      diagnostics.whisper.version = whisperCheck.stdout.trim();
    } catch (error) {
      diagnostics.whisper.error = error.message;
    }

    // Проверяем скрипт транскрипции
    const scriptPath = path.join(__dirname, '..', '..', 'transcription_service.py');
    diagnostics.transcription_script.path = scriptPath;
    try {
      if (fs.existsSync(scriptPath)) {
        diagnostics.transcription_script.exists = true;
      } else {
        diagnostics.transcription_script.error = 'Файл не найден';
      }
    } catch (error) {
      diagnostics.transcription_script.error = error.message;
    }

    res.json({
      success: true,
      diagnostics: diagnostics
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      message: 'Ошибка диагностики системы',
      error: error.message,
      diagnostics: diagnostics
    });
  }
});

// Вспомогательная функция для выполнения команд
function runCommand(command, args) {
  return new Promise((resolve, reject) => {
    const { spawn } = require('child_process');
    const process = spawn(command, args);
    
    let stdout = '';
    let stderr = '';
    
    process.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    
    process.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    
    process.on('close', (code) => {
      if (code === 0) {
        resolve({ stdout, stderr, code });
      } else {
        reject(new Error(`Command failed with code ${code}: ${stderr}`));
      }
    });
    
    process.on('error', (error) => {
      reject(error);
    });
  });
}

module.exports = router; 