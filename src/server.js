const express = require('express');
const cors = require('cors');
const app = express();
const port = process.env.PORT || 3000;
app.use(cors());
app.get('/', (req, res) => res.json({ message: 'Contact Recorder API работает!' }));
app.listen(port, '0.0.0.0', () => console.log('Server running on port', port));
