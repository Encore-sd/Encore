The auth middleware in the remote backend is used to authenticate a JWT token sent in the header of a request. An example of how to use the middle ware on an endpoint is below:

```
const authenticateToken = require('../middleware/auth');

router.get('/protected-route', authenticateToken, async (req, res) => {
    return res.status(200).json({
        success: true,
        message: `Welcome back, user ID ${req.user.userId}!`
    });
});
```

This middle ware should be used for all endpoints that require a user to be authenticated.

Paramaters: authorization header

Return on success:  
	Moves on to the endpoint that called it, while sending the userId from the JWT token

Return on missing token:  
	Status: 401  
	{  
		success: false,  
		message: 'Access token missing. Authorization denied.'  
	}

Return on Invalid or expired token:  
	Status: 403  
	{  
		success: false,  
		message: 'Invalid or expired token.',  
		error: error.message  
	}
