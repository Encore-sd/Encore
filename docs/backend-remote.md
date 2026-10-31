The backend container runs on the port specified in the .env file

## Endpoints

The basic endpoints are located in /backend-remote/server.js
When running in the docker container for local development the base url is: `https://localhost:[remoteBackendPortNumber]`

### Root endpoint /

Purpose: the root endpoint is simply a health check endpoint to tell if the backend server is correctly running.

Return on success:  
	Status: 200  
	'Encore Remote Backend is running'

Return on fail:  
	No return, the remote backend isn't running to return anything.

### /health/postgresql

Purpose: this endpoint is a health check to determine if the backend is successfully connected to the PostgreSQL server and the database is running.

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
