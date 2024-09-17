import os
import datetime

LOG_FILE_PATH = '../logs/auditoria.txt'

def registrar_auditoria(acao, usuario, resultado):
    if not os.path.exists('../logs'):
        os.makedirs('../logs')
    with open(LOG_FILE_PATH, 'a') as log_file:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"{timestamp} - {usuario}: {acao} - Resultado: {resultado}\n")
