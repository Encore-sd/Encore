### sendVerificationEmail = async (email, verificationCode)

Take in two paramaters:  
email - Recipient email address  
verificationCode - A six digit verification code string

This function will then send the user an email with this structure:  
	from: '"Encore Support" <no-reply@encore-rewind.com>',  
	to: email,  
	subject: "Verify Your Encore Account",  
	text: `Your verification code is: ${verificationCode}`,  
	html: `<h3>Welcome to Encore!</h3><p>Your verification code is: <b>${verificationCode}</b></p>`


