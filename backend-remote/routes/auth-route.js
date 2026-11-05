const express = require('express');
const router = express.Router();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { sendVerificationEmail } = require('../utils/auth'); //import utils

const JWT_SECRET = process.env.JWT_SECRET;

// We export a function that accepts the 'pool' so the route has access to it
module.exports = (pool) => {

	//User sign up route
	router.post('/signup', async (req, res) => {
		const {firstName, lastName, email, password} = req.body;

		if (!firstName || !lastName || !email || !password){
			return res.status(400).json({ message: 'FirstName, LastName, Email and password are required.' });
		}

		try {
			// Generate a random 6 digit verification code
			const verificationCode = Math.floor(100000 + Math.random() * 900000).toString();

			//check if the user already exists
			const existingUser = await pool.query('SELECT * FROM users WHERE email = $1', [email]);
			if(existingUser.rows.length > 0){
				const user = existingUser.rows[0];

				//if the user is already verified block registration
				if(user.isverified) {
					return res.status(409).json({ success: false, message: 'User with this email already exists and is verified.' });
				}

				// if they are not verified, resend the email and update the code
				try {
					await sendVerificationEmail(email, verificationCode);
				} catch (error) {
					return res.status(500).json({
						success: false,
						message: 'Failed to send verification email, account was not created',
						error: error.message
					});
				}
				
				//Update the user verification code
				const updateCodeQuery = `
					UPDATE users 
					SET verificationcode = $1 
					WHERE email = $2 
					RETURNING userid, email, isverified;
				`;
				await pool.query(updateCodeQuery, [verificationCode, email]);

				return res.status(200).json({
					success: true,
					message: 'Account already exists but is unverified. A new verification code has been sent to your email.',
					user: newUser.rows[0]
				});
			}

			// Send the new user a verification email
			try {
				await sendVerificationEmail(email, verificationCode);
			} catch (error) {
				return res.status(500).json({
					success: false,
					message: 'Failed to send verification email, account was not created',
					error: error.message
				});
			}

			// Hash the password for the new user
			const saltRounds = 10;
			const passwordHash = await bcrypt.hash(password, saltRounds);

			// Add the new user to the database
			const newUserQuery = `
				INSERT INTO users (firstname, lastname, email, password, verificationcode, isverified)
				VALUES ($1, $2, $3, $4, $5, FALSE)
				RETURNING userid, firstname, lastname, email, isverified;
			`;
			const newUser = await pool.query(newUserQuery, [firstName, lastName, email, passwordHash, verificationCode]);

			// Return success response
			return res.status(201).json({
				success: true,
				message: 'User registered successfully. Please check your email for the verification code.',
				user: newUser.rows[0]
			});

		} catch (error) {
			console.error('Signup error:', error);
			return res.status(500).json({ success: false, message: 'Internal server error during signup.', error: error.message });
		}
	});

	return router;
};












































