const express = require('express');
const PORT = process.env.PORT || 5000;
const healthRoutes = require('./routes/health-route');
const memoriesRoutes = require('./routes/memories-route');

const app = express();

// Middleware to parse JSON bodies
app.use(express.json());

// Basic server status route
app.get('/', (req, res) => {
	res.status(200).send('Encore Local Backend is running!');
});

// Mount the health check routes
app.use('/health', healthRoutes);

// Mount the memories routes
app.use('/memories', memoriesRoutes);

app.listen(PORT, () => {
	console.log(`Local backend is listening on port ${PORT}`);
});
