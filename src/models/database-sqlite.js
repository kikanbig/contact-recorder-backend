const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcryptjs');

// Создание SQLite базы данных
const db = new sqlite3.Database('./data.db');

// Инициализация таблиц базы данных
async function initDatabase() {
  return new Promise((resolve, reject) => {
    db.serialize(async () => {
      try {
        // Таблица пользователей
        db.run(`
          CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            phone TEXT,
            role TEXT DEFAULT 'seller',
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
          )
        `);

        // Таблица локаций
        db.run(`
          CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            city TEXT,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
          )
        `);

        // Таблица аудиозаписей
        db.run(`
          CREATE TABLE IF NOT EXISTS recordings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            location_id INTEGER,
            filename TEXT NOT NULL,
            original_filename TEXT,
            file_path TEXT,
            file_size INTEGER,
            duration_seconds INTEGER,
            mime_type TEXT,
            audio_data BLOB,
            transcription TEXT,
            transcription_language TEXT DEFAULT 'ru',
            transcribed_at DATETIME,
            recording_date DATETIME NOT NULL,
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'uploaded',
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (location_id) REFERENCES locations (id)
          )
        `);

        // Создание админского пользователя
        const adminPasswordHash = await bcrypt.hash('admin123', 10);
        
        db.run(`
          INSERT OR IGNORE INTO users (username, password_hash, full_name, role)
          VALUES (?, ?, ?, ?)
        `, ['admin', adminPasswordHash, 'Администратор', 'admin']);

        // Создание тестовых локаций
        db.run(`
          INSERT OR IGNORE INTO locations (id, name, address, city, description)
          VALUES 
            (1, 'Магазин Центр', 'ул. Ленина, 1', 'Минск', 'Центральный магазин'),
            (2, 'Магазин Восток', 'ул. Сурганова, 10', 'Минск', 'Магазин на востоке города'),
            (3, 'Магазин Запад', 'ул. Притыцкого, 5', 'Минск', 'Магазин на западе города')
        `);

        console.log('✅ SQLite база данных инициализирована успешно');
        resolve();
        
      } catch (error) {
        console.error('❌ Ошибка инициализации SQLite базы данных:', error);
        reject(error);
      }
    });
  });
}

// Функции для работы с базой данных
const dbApi = {
  // Общие функции
  query: (sql, params = []) => {
    return new Promise((resolve, reject) => {
      db.all(sql, params, (err, rows) => {
        if (err) reject(err);
        else resolve({ rows });
      });
    });
  },

  // Пользователи
  async createUser(userData) {
    const { username, email, password_hash, full_name, phone, role = 'seller' } = userData;
    return new Promise((resolve, reject) => {
      db.run(
        'INSERT INTO users (username, email, password_hash, full_name, phone, role) VALUES (?, ?, ?, ?, ?, ?)',
        [username, email, password_hash, full_name, phone, role],
        function(err) {
          if (err) reject(err);
          else {
            db.get('SELECT * FROM users WHERE id = ?', [this.lastID], (err, row) => {
              if (err) reject(err);
              else resolve(row);
            });
          }
        }
      );
    });
  },

  async getUserByUsername(username) {
    return new Promise((resolve, reject) => {
      db.get('SELECT * FROM users WHERE username = ? AND is_active = 1', [username], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  },

  async getUserById(id) {
    return new Promise((resolve, reject) => {
      db.get('SELECT * FROM users WHERE id = ? AND is_active = 1', [id], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  },

  async getAllUsers() {
    return new Promise((resolve, reject) => {
      db.all('SELECT id, username, email, full_name, phone, role, created_at FROM users WHERE is_active = 1 ORDER BY created_at DESC', (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  },

  // Локации
  async createLocation(locationData) {
    const { name, address, city, description } = locationData;
    return new Promise((resolve, reject) => {
      db.run(
        'INSERT INTO locations (name, address, city, description) VALUES (?, ?, ?, ?)',
        [name, address, city, description],
        function(err) {
          if (err) reject(err);
          else {
            db.get('SELECT * FROM locations WHERE id = ?', [this.lastID], (err, row) => {
              if (err) reject(err);
              else resolve(row);
            });
          }
        }
      );
    });
  },

  async getAllLocations() {
    return new Promise((resolve, reject) => {
      db.all('SELECT * FROM locations WHERE is_active = 1 ORDER BY name', (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  },

  async getLocationById(id) {
    return new Promise((resolve, reject) => {
      db.get('SELECT * FROM locations WHERE id = ? AND is_active = 1', [id], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  },

  // Записи
  async createRecording(recordingData) {
    const { 
      user_id, location_id, filename, original_filename, file_path, 
      file_size, duration_seconds, mime_type, audio_data, recording_date, metadata 
    } = recordingData;
    
    return new Promise((resolve, reject) => {
      db.run(`
        INSERT INTO recordings (
          user_id, location_id, filename, original_filename, file_path,
          file_size, duration_seconds, mime_type, audio_data, recording_date, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `, [
        user_id, location_id, filename, original_filename, file_path,
        file_size, duration_seconds, mime_type, audio_data, recording_date, JSON.stringify(metadata)
      ], function(err) {
        if (err) reject(err);
        else {
          db.get('SELECT * FROM recordings WHERE id = ?', [this.lastID], (err, row) => {
            if (err) reject(err);
            else resolve(row);
          });
        }
      });
    });
  },

  async getAllRecordings(limit = 100, offset = 0) {
    return new Promise((resolve, reject) => {
      db.all(`
        SELECT 
          r.*,
          u.username, u.full_name,
          l.name as location_name, l.address as location_address
        FROM recordings r
        LEFT JOIN users u ON r.user_id = u.id
        LEFT JOIN locations l ON r.location_id = l.id
        ORDER BY r.recording_date DESC
        LIMIT ? OFFSET ?
      `, [limit, offset], (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  },

  async getRecordingsByUser(userId, limit = 100, offset = 0) {
    return new Promise((resolve, reject) => {
      db.all(`
        SELECT 
          r.*,
          u.username, u.full_name,
          l.name as location_name, l.address as location_address
        FROM recordings r
        LEFT JOIN users u ON r.user_id = u.id
        LEFT JOIN locations l ON r.location_id = l.id
        WHERE r.user_id = ?
        ORDER BY r.recording_date DESC
        LIMIT ? OFFSET ?
      `, [userId, limit, offset], (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  },

  async getRecordingById(id) {
    return new Promise((resolve, reject) => {
      db.get(`
        SELECT 
          r.*,
          u.username, u.full_name,
          l.name as location_name, l.address as location_address
        FROM recordings r
        LEFT JOIN users u ON r.user_id = u.id
        LEFT JOIN locations l ON r.location_id = l.id
        WHERE r.id = ?
      `, [id], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  },

  async updateRecordingTranscription(id, transcription) {
    return new Promise((resolve, reject) => {
      db.run(
        'UPDATE recordings SET transcription = ?, transcribed_at = CURRENT_TIMESTAMP WHERE id = ?',
        [transcription, id],
        function(err) {
          if (err) reject(err);
          else resolve({ changes: this.changes });
        }
      );
    });
  },

  async getRecordingsStats() {
    return new Promise((resolve, reject) => {
      db.get(`
        SELECT 
          COUNT(*) as total_recordings,
          COUNT(CASE WHEN transcription IS NOT NULL THEN 1 END) as transcribed_recordings,
          COUNT(CASE WHEN transcription IS NULL THEN 1 END) as pending_transcriptions,
          COALESCE(SUM(duration_seconds), 0) as total_duration_seconds
        FROM recordings
      `, (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  }
};

module.exports = { initDatabase, db: dbApi }; 