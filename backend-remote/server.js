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
	res.status(200).send({success: true, message: 'Encore Remote Backend is running!'});
});

// Import and mount the health check routes, passing the pool object
const healthRouter = require('./routes/health-route')(pool);
app.use('/health', healthRouter);

// Import and mount the authentication routes, passing the pool object
const authRouter = require('./routes/auth-route')(pool);
app.use('/auth', authRouter);

// Import and mount the query routes, passing the pool object
// used to process user querries
const queryRouter = require('./routes/query-route')(pool);
app.use('/query', queryRouter);

app.listen(PORT, () => {
	console.log(`Remote backend is listening on port ${PORT}`);
});
