const express = require('express');
const jwt = require('jsonwebtoken');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'contact-recorder-secret-key';

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

// Статические данные локаций (как в мобильном приложении)
const SAMPLE_LOCATIONS = [
  { id: 1, name: '21 Век - Центральный', address: 'ул. Ленина, 45', city: 'Минск', region: 'Минская область' },
  { id: 2, name: '21 Век - Восток', address: 'пр. Независимости, 120', city: 'Минск', region: 'Минская область' },
  { id: 3, name: '21 Век - Запад', address: 'ул. Притыцкого, 83', city: 'Минск', region: 'Минская область' },
  { id: 4, name: '21 Век - Гомель', address: 'ул. Советская, 15', city: 'Гомель', region: 'Гомельская область' },
  { id: 5, name: '21 Век - Брест', address: 'бул. Космонавтов, 32', city: 'Брест', region: 'Брестская область' }
];

// GET /api/locations - Получить список всех активных локаций
router.get('/', authenticateToken, async (req, res) => {
  try {
    res.json({
      success: true,
      locations: SAMPLE_LOCATIONS.map(loc => ({
        id: loc.id,
        name: loc.name,
        address: loc.address,
        city: loc.city,
        region: loc.region,
        createdAt: new Date().toISOString()
      }))
    });
  } catch (error) {
    console.error('Ошибка получения локаций:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка получения локаций'
    });
  }
});

// GET /api/locations/:id - Получить конкретную локацию
router.get('/:id', authenticateToken, async (req, res) => {
  try {
    const { id } = req.params;
    const location = SAMPLE_LOCATIONS.find(loc => loc.id === parseInt(id));
    
    if (!location) {
      return res.status(404).json({
        success: false,
        message: 'Локация не найдена'
      });
    }

    res.json({
      success: true,
      location: {
        id: location.id,
        name: location.name,
        address: location.address,
        city: location.city,
        region: location.region,
        createdAt: new Date().toISOString()
      }
    });
  } catch (error) {
    console.error('Ошибка получения локации:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка получения локации'
    });
  }
});

module.exports = router; 