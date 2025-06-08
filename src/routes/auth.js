const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { Client } = require('pg');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'contact-recorder-secret-key';

// Функция подключения к БД
async function getDbClient() {
  const client = new Client({
    connectionString: process.env.DATABASE_URL,
    ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
  });
  await client.connect();
  return client;
}

// POST /api/auth/login - Авторизация пользователя
router.post('/login', async (req, res) => {
  try {
    const { username, password } = req.body;

    if (!username || !password) {
      return res.status(400).json({
        success: false,
        message: 'Введите логин и пароль'
      });
    }

    // Проверяем пароль (для демо используем простые пароли)
    const validPassword = username === 'продавец1' && password === '123456' ||
                         username === 'продавец2' && password === '123456' ||
                         username === 'администратор' && password === 'admin123';

    if (!validPassword) {
      return res.status(401).json({
        success: false,
        message: 'Неверный логин или пароль'
      });
    }

    // Создаём JWT токен
    const token = jwt.sign(
      { 
        userId: username === 'продавец1' ? 1 : username === 'продавец2' ? 2 : 3, 
        username: username, 
        role: username === 'администратор' ? 'admin' : 'seller'
      },
      JWT_SECRET,
      { expiresIn: '24h' }
    );

    res.json({
      success: true,
      message: 'Авторизация успешна',
      user: {
        id: username === 'продавец1' ? 1 : username === 'продавец2' ? 2 : 3,
        username: username,
        fullName: username === 'продавец1' ? 'Иван Иванов' : username === 'продавец2' ? 'Мария Петрова' : 'Админ Админович',
        role: username === 'администратор' ? 'admin' : 'seller'
      },
      token
    });

  } catch (error) {
    console.error('Ошибка авторизации:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка сервера'
    });
  }
});

// GET /api/auth/me - Получить информацию о текущем пользователе
router.get('/me', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    
    if (!token) {
      return res.status(401).json({
        success: false,
        message: 'Токен не предоставлен'
      });
    }

    const decoded = jwt.verify(token, JWT_SECRET);

    res.json({
      success: true,
      user: {
        id: decoded.userId,
        username: decoded.username,
        fullName: decoded.username === 'продавец1' ? 'Иван Иванов' : decoded.username === 'продавец2' ? 'Мария Петрова' : 'Админ Админович',
        role: decoded.role,
        createdAt: new Date().toISOString()
      }
    });

  } catch (error) {
    console.error('Ошибка получения пользователя:', error);
    res.status(401).json({
      success: false,
      message: 'Недействительный токен'
    });
  }
});

module.exports = router; 