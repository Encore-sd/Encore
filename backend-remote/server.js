const express = require('express');
const { Pool } = require('pg');

const app = express();
const PORT = process.env.PORT || 5001;

// Middleware to parse JSON bodies
app.use(express.json());

// Set up PostgreSQL connection pool using environment variables from Docker Compose
const pool = new Pool({
	host: process.env.DB_HOST,
	user: process.env.DB_USER,
	password: process.env.DB_PASSWORD,
	database: process.env.DB_NAME,
	port: process.env.DB_PORT || 5432,
});

// Basic root health check route
app.get('/', (req, res) => {
	res.status(200).send('Encore Remote Backend is running!');
});

// Import and mount the health check routes, passing the pool object
const healthRoutes = require('./routes/health-route')(pool);
app.use('/health', healthRoutes);

app.listen(PORT, () => {
	console.log(`Remote backend is listening on port ${PORT}`);
});
