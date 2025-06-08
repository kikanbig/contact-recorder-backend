const express = require("express");
const cors = require("cors");
const { Client } = require("pg");

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.get("/", (req, res) => {
  res.json({ 
    message: "Contact Recorder API работает!", 
    status: "OK", 
    timestamp: new Date().toISOString() 
  });
});

app.get("/health", (req, res) => {
  res.json({ 
    status: "healthy", 
    uptime: process.uptime(),
    timestamp: new Date().toISOString()
  });
});

// Start server
app.listen(port, "0.0.0.0", () => {
  console.log("✅ Contact Recorder API запущен на порту", port);
  console.log("🌐 Сервер доступен по адресу: http://0.0.0.0:" + port);
  console.log("🗄️ DATABASE_URL:", process.env.DATABASE_URL ? "✅ Настроен" : "❌ Не найден");
});
