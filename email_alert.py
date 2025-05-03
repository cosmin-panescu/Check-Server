import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

def email_alert(subject, body, to):
    msg = EmailMessage()
    msg.set_content(body)
    msg['subject'] = subject
    msg['to'] = to

    user = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASSWORD")
    msg['from'] = user

    if not user or not password:
        raise Exception("EMAIL_USER sau EMAIL_PASSWORD nu sunt setate.")

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(user, password)
    server.send_message(msg)
    server.quit()