const express = require('express');
const jwt = require('jsonwebtoken');
const { db } = require('../models/database');

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

// GET /api/locations - Получить список всех локаций
router.get('/', authenticateToken, async (req, res) => {
  try {
    const locations = await db.getAllLocations();
    
    res.json({
      success: true,
      locations: locations.map(location => ({
        id: location.id,
        name: location.name,
        address: location.address,
        city: location.city,
        description: location.description,
        is_active: location.is_active,
        created_at: location.created_at
      })),
      total: locations.length
    });

  } catch (error) {
    console.error('Ошибка получения локаций:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка получения списка локаций'
    });
  }
});

// GET /api/locations/:id - Получить конкретную локацию
router.get('/:id', authenticateToken, async (req, res) => {
  try {
    const location = await db.getLocationById(req.params.id);
    
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
        description: location.description,
        is_active: location.is_active,
        created_at: location.created_at,
        updated_at: location.updated_at
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

// POST /api/locations - Создать новую локацию (только для администраторов)
router.post('/', authenticateToken, requireAdmin, async (req, res) => {
  try {
    const { name, address, city, description } = req.body;

    if (!name) {
      return res.status(400).json({
        success: false,
        message: 'Название локации обязательно'
      });
    }

    const newLocation = await db.createLocation({
      name,
      address,
      city,
      description
    });

    res.json({
      success: true,
      message: 'Локация успешно создана',
      location: {
        id: newLocation.id,
        name: newLocation.name,
        address: newLocation.address,
        city: newLocation.city,
        description: newLocation.description,
        is_active: newLocation.is_active,
        created_at: newLocation.created_at
      }
    });

  } catch (error) {
    console.error('Ошибка создания локации:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка создания локации'
    });
  }
});

// PUT /api/locations/:id - Обновить локацию (только для администраторов)
router.put('/:id', authenticateToken, requireAdmin, async (req, res) => {
  try {
    const { name, address, city, description, is_active } = req.body;
    
    // Проверяем существование локации
    const existingLocation = await db.getLocationById(req.params.id);
    if (!existingLocation) {
      return res.status(404).json({
        success: false,
        message: 'Локация не найдена'
      });
    }

    const result = await db.query(
      `UPDATE locations 
       SET name = $1, address = $2, city = $3, description = $4, is_active = $5, updated_at = CURRENT_TIMESTAMP
       WHERE id = $6 
       RETURNING *`,
      [
        name || existingLocation.name,
        address !== undefined ? address : existingLocation.address,
        city || existingLocation.city,
        description !== undefined ? description : existingLocation.description,
        is_active !== undefined ? is_active : existingLocation.is_active,
        req.params.id
      ]
    );

    res.json({
      success: true,
      message: 'Локация успешно обновлена',
      location: {
        id: result.rows[0].id,
        name: result.rows[0].name,
        address: result.rows[0].address,
        city: result.rows[0].city,
        description: result.rows[0].description,
        is_active: result.rows[0].is_active,
        updated_at: result.rows[0].updated_at
      }
    });

  } catch (error) {
    console.error('Ошибка обновления локации:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка обновления локации'
    });
  }
});

// DELETE /api/locations/:id - Деактивировать локацию (только для администраторов)
router.delete('/:id', authenticateToken, requireAdmin, async (req, res) => {
  try {
    const existingLocation = await db.getLocationById(req.params.id);
    if (!existingLocation) {
      return res.status(404).json({
        success: false,
        message: 'Локация не найдена'
      });
    }

    // Деактивируем локацию вместо полного удаления
    await db.query(
      'UPDATE locations SET is_active = false, updated_at = CURRENT_TIMESTAMP WHERE id = $1',
      [req.params.id]
    );

    res.json({
      success: true,
      message: 'Локация деактивирована'
    });

  } catch (error) {
    console.error('Ошибка деактивации локации:', error);
    res.status(500).json({
      success: false,
      message: 'Ошибка деактивации локации'
    });
  }
});

module.exports = router; 