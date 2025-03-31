import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from website.fim_utils import  fim_logger
# Constants for the email
SENDER_EMAIL = "rajairethomas10@gmail.com"  # Sender email
SENDER_PASSWORD = "wlaj vcwq ksew dmzd"  #"mkpn arvm gmph xvwy" Sender email password or app password for Gmail
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # SSL port for Gmail

# Logging setup (if required)


def send_critical_alert(recipients, added_files, deleted_files, modified_files):
    """Send a modern HTML email to all admins when critical files are altered."""
    
    subject = "🚨 URGENT: Critical File Integrity Violation Detected! 🚨"

    # Modern Email Design
    content_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: red;">🚨 File Integrity Alert 🚨</h2>
        <p>The File Integrity Monitoring (FIM) system detected unauthorized modifications.</p>
        <table border="1" cellspacing="0" cellpadding="8" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f8d7da;">
                <th style="padding: 10px; text-align: left;">Action</th>
                <th style="padding: 10px; text-align: left;">Affected Files</th>
            </tr>
            <tr>
                <td style="color: red;">Added</td>
                <td>{", ".join(added_files) if added_files else "None"}</td>
            </tr>
            <tr>
                <td style="color: red;">Deleted</td>
                <td>{", ".join(deleted_files) if deleted_files else "None"}</td>
            </tr>
            <tr>
                <td style="color: red;">Modified</td>
                <td>{", ".join(modified_files) if modified_files else "None"}</td>
            </tr>
        </table>
        <p><strong>Immediate action is required!</strong> Review the changes and restore backups if necessary.</p>
    </body>
    </html>
    """

    for recipient in recipients:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient
        msg['Subject'] = subject

        # Attach the HTML content
        msg.attach(MIMEText(content_html, 'html'))

        try:
            # Set up the SMTP server
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                # Send the email
                server.sendmail(SENDER_EMAIL, recipient, msg.as_string())
                fim_logger.info(f"Email sent successfully to {recipient}")
        except Exception as e:
            fim_logger.error(f"Error sending email to {recipient}: {e}")
