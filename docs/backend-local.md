The backend container runs on the port specified in the .env file

## Endpoints

The basic endpoints are located in /backend-local/server.js
When running in the docker container for local development the base url is: `https://localhost:[localBackendPortNumber]`

### Root endpoint /

Purpose: the root endpoint is simply a health check endpoint to tell if the backend server is correctly running.

Return on success:  
	Status: 200  
	'Encore Local Backend is running'

Return on fail:  
	No return, the local backend isn't running to return anything.

### /health/remote

Purpose: Check that the remote backend is running and reachable by the local backend

Return on success:  
	Status: 200  
	{  
		status: 'connected',  
        remoteUrl: REMOTE_BACKEND_URL,  
        responseMessage: text  
	}  

Return on remote backend refuse connection:
	Status: 502  
	{  
		status: 'unreachable',  
        remoteUrl: REMOTE_BACKEND_URL,  
        error: `Remote server responded with status: ${response.status}`  
	}  

Return on remote backend unreachable:
	Status: 503  
	{  
		status: 'offline',  
		remoteUrl: REMOTE_BACKEND_URL,  
		message: 'Could not reach remote backend. Operating in offline mode.',  
		error: error.message  
	}  

### /health/sqlite

Purpose: this endpoint is a health check to determine if the local backend has successfully set up the SQLite database

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
