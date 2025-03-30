import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

#SendGrid API key
SENDGRID_API_KEY = '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'

# Set up the SendGrid client
sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)

def send_email_outlook(recipient_email):
    from_email = Email("seville123@outlook.com")  #outlook email
    to_email = To(recipient_email)
    subject = "Admin receiving Email - EMERGENCY"
    content = Content("text/plain", "This is an automated test email sent from Outlook using SendGrid.")

    mail = Mail(from_email, to_email, subject, content)

    try:
        #Send email using SendGrid API
        response = sg.send(mail)
        print(f"Email sent successfully! Status code: {response.status_code}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False