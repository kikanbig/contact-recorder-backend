const { Client, Pool } = require('pg');

// Создание пула подключений
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 30000,
  query_timeout: 30000,
  statement_timeout: 30000,
  keepAlive: true,
  keepAliveInitialDelayMillis: 5000,
  application_name: 'contact_recorder_backend'
});

// Функция для повторных попыток подключения
async function connectWithRetry(maxRetries = 5, delay = 2000) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      console.log(`🔄 Попытка подключения к БД ${i + 1}/${maxRetries}...`);
      const client = await pool.connect();
      console.log('✅ Подключение к БД успешно!');
      return client;
    } catch (error) {
      console.error(`❌ Ошибка подключения к БД (попытка ${i + 1}):`, error.message);
      if (i === maxRetries - 1) {
        throw error;
      }
      console.log(`⏳ Ожидание ${delay}ms перед следующей попыткой...`);
      await new Promise(resolve => setTimeout(resolve, delay));
      delay *= 1.5; // Увеличиваем задержку
    }
  }
}

// Инициализация таблиц базы данных
async function initDatabase() {
  const client = await connectWithRetry();
  
  try {
    // Таблица пользователей (продавцов)
    await client.query(`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        email VARCHAR(255) UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        full_name VARCHAR(255),
        phone VARCHAR(20),
        role VARCHAR(50) DEFAULT 'seller',
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Таблица локаций
    await client.query(`
      CREATE TABLE IF NOT EXISTS locations (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        address TEXT,
        city VARCHAR(100),
        description TEXT,
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Таблица аудиозаписей
    await client.query(`
      CREATE TABLE IF NOT EXISTS recordings (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
        filename VARCHAR(255) NOT NULL,
        original_filename VARCHAR(255),
        file_path TEXT,
        file_size BIGINT,
        duration_seconds INTEGER,
        mime_type VARCHAR(100),
        audio_data BYTEA,
        transcription TEXT,
        transcription_language VARCHAR(10) DEFAULT 'ru',
        transcribed_at TIMESTAMP,
        recording_date TIMESTAMP NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(50) DEFAULT 'uploaded',
        metadata JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Индексы для оптимизации
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_recordings_user_id ON recordings(user_id);
    `);
    
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_recordings_location_id ON recordings(location_id);
    `);
    
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_recordings_recording_date ON recordings(recording_date);
    `);
    
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_recordings_status ON recordings(status);
    `);

    // Создание админского пользователя по умолчанию
    const bcrypt = require('bcryptjs');
    const adminPasswordHash = await bcrypt.hash('admin123', 10);
    
    await client.query(`
      INSERT INTO users (username, password_hash, full_name, role)
      VALUES ($1, $2, $3, $4)
      ON CONFLICT (username) DO NOTHING
    `, ['admin', adminPasswordHash, 'Администратор', 'admin']);

    // Создание тестовых локаций
    await client.query(`
      INSERT INTO locations (name, address, city, description)
      VALUES 
        ($1, $2, $3, $4),
        ($5, $6, $7, $8),
        ($9, $10, $11, $12)
      ON CONFLICT DO NOTHING
    `, [
      'Магазин Центр', 'ул. Ленина, 1', 'Минск', 'Центральный магазин',
      'Магазин Восток', 'ул. Сурганова, 10', 'Минск', 'Магазин на востоке города',
      'Магазин Запад', 'ул. Притыцкого, 5', 'Минск', 'Магазин на западе города'
    ]);

    console.log('✅ База данных инициализирована успешно');
    
  } catch (error) {
    console.error('❌ Ошибка инициализации базы данных:', error);
    throw error;
  } finally {
    client.release();
  }
}

// Функции для работы с базой данных
const db = {
  // Общие функции
  query: async (text, params) => {
    try {
      return await pool.query(text, params);
    } catch (error) {
      console.error('❌ Ошибка выполнения запроса:', error.message);
      throw error;
    }
  },
  getClient: () => connectWithRetry(),
  
  // Пользователи
  async createUser(userData) {
    const { username, email, password_hash, full_name, phone, role = 'seller' } = userData;
    const result = await pool.query(
      'INSERT INTO users (username, email, password_hash, full_name, phone, role) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *',
      [username, email, password_hash, full_name, phone, role]
    );
    return result.rows[0];
  },

  async getUserByUsername(username) {
    const result = await pool.query('SELECT * FROM users WHERE username = $1 AND is_active = true', [username]);
    return result.rows[0];
  },

  async getUserById(id) {
    const result = await pool.query('SELECT * FROM users WHERE id = $1 AND is_active = true', [id]);
    return result.rows[0];
  },

  async getAllUsers() {
    const result = await pool.query('SELECT id, username, email, full_name, phone, role, created_at FROM users WHERE is_active = true ORDER BY created_at DESC');
    return result.rows;
  },

  // Локации
  async createLocation(locationData) {
    const { name, address, city, description } = locationData;
    const result = await pool.query(
      'INSERT INTO locations (name, address, city, description) VALUES ($1, $2, $3, $4) RETURNING *',
      [name, address, city, description]
    );
    return result.rows[0];
  },

  async getAllLocations() {
    const result = await pool.query('SELECT * FROM locations WHERE is_active = true ORDER BY name');
    return result.rows;
  },

  async getLocationById(id) {
    const result = await pool.query('SELECT * FROM locations WHERE id = $1 AND is_active = true', [id]);
    return result.rows[0];
  },

  // Записи
  async createRecording(recordingData) {
    const { 
      user_id, location_id, filename, original_filename, file_path, 
      file_size, duration_seconds, mime_type, audio_data, recording_date, metadata 
    } = recordingData;
    
    const result = await pool.query(`
      INSERT INTO recordings (
        user_id, location_id, filename, original_filename, file_path,
        file_size, duration_seconds, mime_type, audio_data, recording_date, metadata
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11) RETURNING *
    `, [
      user_id, location_id, filename, original_filename, file_path,
      file_size, duration_seconds, mime_type, audio_data, recording_date, metadata
    ]);
    
    return result.rows[0];
  },

  async getAllRecordings(limit = 100, offset = 0) {
    const result = await pool.query(`
      SELECT 
        r.*,
        u.username, u.full_name,
        l.name as location_name, l.address as location_address
      FROM recordings r
      LEFT JOIN users u ON r.user_id = u.id
      LEFT JOIN locations l ON r.location_id = l.id
      ORDER BY r.recording_date DESC
      LIMIT $1 OFFSET $2
    `, [limit, offset]);
    
    return result.rows;
  },

  async getRecordingsByUser(userId, limit = 100, offset = 0) {
    const result = await pool.query(`
      SELECT 
        r.*,
        l.name as location_name, l.address as location_address
      FROM recordings r
      LEFT JOIN locations l ON r.location_id = l.id
      WHERE r.user_id = $1
      ORDER BY r.recording_date DESC
      LIMIT $2 OFFSET $3
    `, [userId, limit, offset]);
    
    return result.rows;
  },

  async getRecordingById(id) {
    const result = await pool.query(`
      SELECT 
        r.*,
        u.username, u.full_name,
        l.name as location_name, l.address as location_address
      FROM recordings r
      LEFT JOIN users u ON r.user_id = u.id
      LEFT JOIN locations l ON r.location_id = l.id
      WHERE r.id = $1
    `, [id]);
    
    return result.rows[0];
  },

  async updateRecordingTranscription(id, transcription) {
    const result = await pool.query(`
      UPDATE recordings 
      SET transcription = $1, transcribed_at = CURRENT_TIMESTAMP, status = 'transcribed'
      WHERE id = $2 
      RETURNING *
    `, [transcription, id]);
    
    return result.rows[0];
  },

  async getRecordingsStats() {
    const result = await pool.query(`
      SELECT 
        COUNT(*) as total_recordings,
        COUNT(CASE WHEN transcription IS NOT NULL THEN 1 END) as transcribed_recordings,
        COUNT(DISTINCT user_id) as unique_users,
        COUNT(DISTINCT location_id) as unique_locations,
        SUM(duration_seconds) as total_duration_seconds,
        AVG(duration_seconds) as avg_duration_seconds
      FROM recordings
    `);
    
    return result.rows[0];
  }
};

module.exports = { db, initDatabase, pool }; 