import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from dotenv import load_dotenv


def send_email_with_attachments(subject, message, recipient_emails, attachment_paths):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    # Setup the MIME
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipient_emails)
    msg['Subject'] = subject

    # Attach the message to the MIME message
    msg.attach(MIMEText(message, 'plain'))

    # Attach files to the email
    for attachment_path in attachment_paths:
        part = MIMEBase('application', "octet-stream")
        with open(attachment_path, 'rb') as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)

        filename = attachment_path.split('\\')[-1]
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        msg.attach(part)

    # Create SMTP session for sending the mail
    try:
        _send_email(
            sender_email, sender_password, msg, recipient_emails
        )
    except Exception as e:
        print(f"Failed to send email with attachments to {recipient_emails}. Error: {e}")


# TODO Rename this here and in `send_email_with_attachments`
def _send_email(sender_email, sender_password, msg, recipient_emails):
    server = smtplib.SMTP('smtp.gmail.com', 587) # Use appropriate SMTP server details
    server.starttls() # Enable security
    server.login(sender_email, sender_password) # Login with mail_id and password
    text = msg.as_string()
    server.sendmail(sender_email, recipient_emails, text)
    server.quit()
    print(f"Email with attachments sent successfully to {recipient_emails}")


if __name__=="__main__":
    # Load environment variables from .env file
    load_dotenv()

    # send_email_with_attachments("Test Subject", "Test Message", "mrinalrajprom1@gmail.com", 
                                # [])
    send_email_with_attachments("UTBotStochasticRSI Buy/Sell Stocks", "Please find 2 csv files attached",
                                ["mrinalrajubereats1@gmail.com"], 
                                [r"c:\Users\mrina\cursor-projects\UTBotStochasticRsi\python\output\2024-04-02_buy_stocks.csv", r"c:\Users\mrina\cursor-projects\UTBotStochasticRsi\python\output\2024-04-02_exit_stocks.csv"])

