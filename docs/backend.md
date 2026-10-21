The backend container runs on the port specified in the .env file

The base url for the backend is: `https://localhost:[backendPortNumber]`

## Endpoints

The basic endpoints are located in /backend/server.js
When running in the docker container for local development the base url is: `http://localhost:[backend_port_number]`

### Root endpoint /

Purpose: the root endpoint is simply a health check endpoint to tell if the backend server is correctly running.

Return on success:  
	Status: 200  
	'Encore Backend is running'

Return on fail:  
	No return, the backend isn't running to return anything.

### /db-health

Purpose: this endpoint is a health check to determine if the backend is successfully connected to the mongodb server and the database is running.

Return on success:  
	Status: 200  
	{  
		success: true,  
		time: result.rows[0].now  
	}

Return on fail:  
	Status: 500  
	{  
		success: false,  
		error: err.message  
	}

### /sqlite-health

Purpose: this endpoint is a health check to determine if the backend is successfully connected to the sqlite database, and that the sqlite file exists.

Return on success:  
	Status: 200  
	{  
		status: 'healthy',  
		database: 'SQLite (Local)',  
		tablesFound: tables.map(t => t.name)  
	}

Return on fail:  
	Status: 500  
	{  
		status: 'unhealthy',  
		error: error.message  
	}  
