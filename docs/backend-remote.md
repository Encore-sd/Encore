The backend container runs on the port specified in the .env file

## Endpoints

The basic endpoints are located in /backend-remote/server.js
When running in the docker container for local development the base url is: `https://localhost:[remoteBackendPortNumber]`

### GET Root endpoint /

Purpose: the root endpoint is simply a health check endpoint to tell if the backend server is correctly running.

Paramaters: None

Protected route: false

Return on success:  
	Status: 200  
	'Encore Remote Backend is running'

Return on fail:  
	No return, the remote backend isn't running to return anything.

### GET /health/postgresql

Purpose: this endpoint is a health check to determine if the backend is successfully connected to the PostgreSQL server and the database is running.

Paramaters: None

Protected route: false

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

### POST /auth/signup

Purpose: This endpoint allows a new user to sign up for an account and sends them a verification email.  
If the user account already exists, but has not been verified, a new verification email is sent.

Paramaters: None  
Body: firstName, lastName, email, password

Protected route: false

Return on success:  
	Status: 201  
	{  
		success: true,  
		message: 'User registered successfully. Please check your email for the verification code.',
		user: newUser.rows[0]
	}

Return on User already exists, but has not been verified:  
	status: 200  
	{  
		success: true,  
		message: 'Account already exists but is unverified. A new verification code has been sent to your email.'  
	}  

Return on user already exists, and has been verified:  
	Status: 409  
	{  
		success: false,
		message: 'User with this email already exists and is verified.'
	}

Return on missing body:  
	Status: 400  
	{  
		success: false,
		message: 'FirstName, LastName, Email and password are required.'
	}

Return on failed to send email:  
	status: 500  
	{  
		success: false,  
		message: 'Failed to send verification email, account was not created'
		error: errorMessage
	}

Return on failed to create user account:  
	status: 500  
	{  
		success: false,
		message: 'Internal server error during signup.',
		error: errorMessage
	}







