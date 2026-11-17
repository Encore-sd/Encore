const nodemailer = require('nodemailer');

//configure transporter using environment variables
const transporter = nodemailer.createTransport({
	host: process.env.EMAIL_HOST || 'smtp.mailtrap.io',
	port: process.env.EMAIL_PORT || 2525,
	auth: {
		user: process.env.EMAIL_USER || '',
		pass: process.env.EMAIL_PASSWORD || ''
	}
});

/*
Sends a 6 digit verification code email to the user
@param {string} email - Recipient email address
@param {string} verificationCode - 6 digit verification code string
*/
const sendVerificationEmail = async (email, verificationCode) => {
	try {
		await transporter.sendMail({
			from: '"Encore Support" <no-reply@encore-rewind.com>',
			to: email,
			subject: "Verify Your Encore Account",
			text: `Your verification code is: ${verificationCode}`,
			html: `<h3>Welcome to Encore!</h3><p>Your verification code is: <b>${verificationCode}</b></p>`
		});
		return true;
	} catch (error){
		throw error;
	}
};

module.exports = {
	sendVerificationEmail
}
