import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

# Detalhes do servidor de e-mail
EMAIL_HOST = 'smtp.brasmol.com.br'
EMAIL_PORT = 587
EMAIL_USER = 'rh@brasmol.com.br'
EMAIL_PASSWORD = 'Brasmol@2024'

def enviar_email_com_anexo(destinatario, assunto, corpo_html, anexo):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = destinatario
        msg['Subject'] = assunto

        # Corpo do e-mail em HTML (essa linha é onde ocorre a mudança importante)
        msg.attach(MIMEText(corpo_html, 'html'))  # Altera para 'html' em vez de 'plain'

        # Anexo
        with open(anexo, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(anexo)}')
            msg.attach(part)

        # Enviar e-mail
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()  # Usar TLS para criptografia
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, destinatario, text)
        server.quit()
        print(f"E-mail enviado para {destinatario}")

    except Exception as e:
        print(f"Erro ao enviar e-mail para {destinatario}: {e}")
