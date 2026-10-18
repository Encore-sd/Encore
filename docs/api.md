## Endpoints:  

If running the application in the dev container the endpoint base url is: `http://localhost:[backendPortNumber]`  

### /  

This is the root endpoint and it serves as a health check for the backend server.  

**Return on Success**  
	Status: 200  
	'Encore Backend is running!'  

### /db-health  

This endpoint servers as a health check for the database.  

**Return on Success**  
	Status: 200  
	{  
		success: true,  
		time: result.rows[0].now  
	}  

**Return on Fail**  
	Status: 500  
	{  
		success: false,
		error: err.message
	}  
