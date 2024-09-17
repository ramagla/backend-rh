import os
import pdfplumber
import re
from PyPDF2 import PdfReader, PdfWriter
import io
import zipfile

def dividir_pdf_em_paginas(pdf_file_path):
    reader = PdfReader(pdf_file_path)
    num_paginas = len(reader.pages)
    
    paginas_separadas = []

    for i in range(num_paginas):
        writer = PdfWriter()
        writer.add_page(reader.pages[i])

        output_filename = f"uploads/pagina_{i+1}.pdf"
        with open(output_filename, "wb") as output_pdf:
            writer.write(output_pdf)
            paginas_separadas.append(output_filename)
            print(f"Arquivo salvo: {output_filename}")

    return paginas_separadas

def extrair_nome_do_pdf(caminho_pdf):
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            texto = ""
            for pagina in pdf.pages:
                texto += pagina.extract_text()

            padrao_nome = re.compile(r'Código\s+Nome do Funcionário\s+CBO\s+Departamento\s+Filial.*\n(\d+\s+([A-Za-z\s]+))')
            resultado = padrao_nome.search(texto)

            if resultado:
                nome = resultado.group(2).strip()
                print(f"Nome encontrado: {nome}")
                return nome
    except Exception as e:
        print(f"Erro ao processar {caminho_pdf}: {e}")
    return None

def renomear_com_funcionarios(arquivos_paginas):
    novos_nomes = []
    for arquivo in arquivos_paginas:
        nome_funcionario = extrair_nome_do_pdf(arquivo)
        if nome_funcionario:
            novo_nome = f"{nome_funcionario}.pdf"
            print(f"Renomeando {arquivo} para {novo_nome}")
        else:
            novo_nome = os.path.basename(arquivo)
            print(f"Nome não encontrado. Mantendo nome original: {novo_nome}")
        novos_nomes.append(novo_nome)
    return novos_nomes

def renomear_e_zipar(arquivos, novos_nomes):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for i, arquivo in enumerate(arquivos):
            novo_nome = novos_nomes[i]
            zip_file.write(arquivo, novo_nome)
    zip_buffer.seek(0)
    return zip_buffer
