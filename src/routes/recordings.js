const express = require('express');
const jwt = require('jsonwebtoken');
const fs = require('fs');
const path = require('path');
const multer = require('multer');
const { OpenAI } = require('openai');

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
    const allowedTypes = ['audio/mpeg', 'audio/mp4', 'audio/m4a', 'audio/wav', 'audio/webm'];
    if (allowedTypes.includes(file.mimetype) || file.originalname.endsWith('.m4a')) {
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
    req.user = decoded;
    next();
  } catch (error) {
    res.status(401).json({
      success: false,
      message: 'Недействительный токен'
    });
  }
}

// Временное хранилище записей (в production будет база данных)
let recordings = [];

// POST /api/recordings/upload - Загрузка метаданных записи
router.post('/upload', authenticateToken, async (req, res) => {
  try {
    const { 
      fileName, 
      duration, 
      locationId, 
      fileSize,
      recordingTime 
    } = req.body;

    if (!fileName || !duration) {
      return res.status(400).json({
        success: false,
        message: 'Необходимы fileName и duration'
      });
    }

    const recording = {
      id: Date.now().toString(),
      userId: req.user.userId,
      fileName,
      duration,
      locationId,
      fileSize,
      recordingTime: recordingTime || new Date().toISOString(),
      uploadedAt: new Date().toISOString(),
      status: 'uploaded'
    };

    recordings.push(recording);

    res.json({
      success: true,
      message: 'Запись успешно загружена',
      recording: {
        id: recording.id,
        fileName: recording.fileName,
        duration: recording.duration,
        uploadedAt: recording.uploadedAt
      }
    });

  } catch (error) {
    console.error('Ошибка загрузки записи:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка загрузки записи'
    });
  }
});

// GET /api/recordings - Получить список записей пользователя
router.get('/', authenticateToken, async (req, res) => {
  try {
    const userRecordings = recordings.filter(r => r.userId === req.user.userId);
    
    res.json({
      success: true,
      recordings: userRecordings.map(recording => ({
        id: recording.id,
        fileName: recording.fileName,
        duration: recording.duration,
        locationId: recording.locationId,
        fileSize: recording.fileSize,
        recordingTime: recording.recordingTime,
        uploadedAt: recording.uploadedAt,
        status: recording.status
      })),
      total: userRecordings.length
    });

  } catch (error) {
    console.error('Ошибка получения записей:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка получения записей'
    });
  }
});

// DELETE /api/recordings/:id - Удалить запись
router.delete('/:id', authenticateToken, async (req, res) => {
  try {
    const { id } = req.params;
    
    const recordingIndex = recordings.findIndex(
      r => r.id === id && r.userId === req.user.userId
    );

    if (recordingIndex === -1) {
      return res.status(404).json({
        success: false,
        message: 'Запись не найдена'
      });
    }

    recordings.splice(recordingIndex, 1);

    res.json({
      success: true,
      message: 'Запись удалена'
    });

  } catch (error) {
    console.error('Ошибка удаления записи:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка удаления записи'
    });
  }
});

// GET /api/recordings/stats - Статистика записей
router.get('/stats', authenticateToken, async (req, res) => {
  try {
    const userRecordings = recordings.filter(r => r.userId === req.user.userId);
    
    const stats = {
      totalRecordings: userRecordings.length,
      totalDuration: userRecordings.reduce((sum, r) => sum + (r.duration || 0), 0),
      averageDuration: userRecordings.length > 0 
        ? userRecordings.reduce((sum, r) => sum + (r.duration || 0), 0) / userRecordings.length 
        : 0,
      recordingsToday: userRecordings.filter(r => {
        const today = new Date().toDateString();
        const recordingDate = new Date(r.recordingTime).toDateString();
        return today === recordingDate;
      }).length
    };

    res.json({
      success: true,
      stats
    });

  } catch (error) {
    console.error('Ошибка получения статистики:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка получения статистики'
    });
  }
});

// POST /api/recordings/transcribe - Транскрипция аудио через файл
router.post('/transcribe', authenticateToken, upload.single('audio'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        message: 'Аудио файл не предоставлен'
      });
    }

    if (!openai) {
      return res.status(500).json({
        success: false,
        message: 'OpenAI API ключ не настроен'
      });
    }

    const { userId, locationId, duration, recordingTime } = req.body;

    console.log('📝 Начинаем транскрипцию файла:', req.file.originalname);
    console.log('📊 Размер файла:', req.file.size, 'байт');

    // Выполняем транскрипцию через OpenAI Whisper
    const transcription = await openai.audio.transcriptions.create({
      file: fs.createReadStream(req.file.path),
      model: 'whisper-1',
      language: 'ru',
      response_format: 'text'
    });

    console.log('✅ Транскрипция завершена:', transcription.substring(0, 100) + '...');

    // Создаем запись в базе данных
    const recording = {
      id: Date.now().toString(),
      userId: userId || req.user.userId,
      fileName: req.file.originalname,
      duration: parseInt(duration) || 0,
      locationId: locationId || 'unknown',
      recordingTime: recordingTime || new Date().toISOString(),
      uploadedAt: new Date().toISOString(),
      transcription: transcription,
      transcribedAt: new Date().toISOString(),
      status: 'transcribed'
    };

    recordings.push(recording);

    // Удаляем временный файл
    fs.unlink(req.file.path, (err) => {
      if (err) console.error('Ошибка удаления временного файла:', err);
    });

    res.json({
      success: true,
      message: 'Транскрипция завершена успешно',
      recording: {
        id: recording.id,
        transcription: recording.transcription,
        transcribedAt: recording.transcribedAt,
        duration: recording.duration
      }
    });

  } catch (error) {
    console.error('❌ Ошибка транскрипции:', error);
    
    // Удаляем временный файл при ошибке
    if (req.file) {
      fs.unlink(req.file.path, (err) => {
        if (err) console.error('Ошибка удаления временного файла:', err);
      });
    }

    res.status(500).json({
      success: false,
      message: 'Ошибка при транскрипции',
      error: error.message
    });
  }
});

// POST /api/recordings/:id/transcribe - Транскрипция существующей записи (совместимость)
router.post('/:id/transcribe', authenticateToken, async (req, res) => {
  try {
    const { id } = req.params;
    
    const recording = recordings.find(r => r.id === id && r.userId === req.user.userId);
    
    if (!recording) {
      return res.status(404).json({
        success: false,
        message: 'Запись не найдена'
      });
    }

    if (recording.transcription) {
      return res.json({
        success: true,
        message: 'Транскрипция уже существует',
        transcription: recording.transcription,
        transcribedAt: recording.transcribedAt
      });
    }

    res.json({
      success: false,
      message: 'Для транскрипции используйте POST /api/recordings/transcribe с аудио файлом'
    });

  } catch (error) {
    console.error('Ошибка транскрипции:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка при транскрипции'
    });
  }
});

// GET /api/recordings/:id/transcription - Получить транскрипцию записи
router.get('/:id/transcription', authenticateToken, async (req, res) => {
  try {
    const { id } = req.params;
    
    const recording = recordings.find(r => r.id === id && r.userId === req.user.userId);
    
    if (!recording) {
      return res.status(404).json({
        success: false,
        message: 'Запись не найдена'
      });
    }

    if (!recording.transcription) {
      return res.status(404).json({
        success: false,
        message: 'Транскрипция не найдена'
      });
    }

    res.json({
      success: true,
      transcription: recording.transcription,
      transcribedAt: recording.transcribedAt,
      recording: {
        id: recording.id,
        fileName: recording.fileName,
        duration: recording.duration,
        recordingTime: recording.recordingTime
      }
    });

  } catch (error) {
    console.error('Ошибка получения транскрипции:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка получения транскрипции'
    });
  }
});

module.exports = router; 