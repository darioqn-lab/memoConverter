# -*- coding: utf-8 -*-
"""
preparar.py
Roda NA SUA MAQUINA (com Python instalado) para montar o kit do colega.
Uso: python preparar.py

O que faz:
1. Baixa o Python 3.8.10 embeddable
2. Extrai e configura o Python
3. Baixa e instala os pacotes necessarios
4. Monta a pasta MemoConverter_Portatil/ pronta para o colega

O colega recebe a pasta MemoConverter_Portatil/ e clica em MemoConverter.bat.
Sem scripts de instalacao, sem terminal, sem complicacao.
"""

import os
import sys
import shutil
import zipfile
import urllib.request
import subprocess
from pathlib import Path

BASE    = Path(__file__).parent
DESTINO = BASE / "MemoConverter_Portatil"
PYTHON_URL = "https://www.python.org/ftp/python/3.8.10/python-3.8.10-embed-amd64.zip"
PYTHON_ZIP = BASE / "python-3.8.10-embed-amd64.zip"
PYTHON_DIR = DESTINO / "python"
APP_DIR    = DESTINO / "app"
PKGS_DIR   = PYTHON_DIR / "Lib" / "site-packages"


def log(msg):
    print(msg)


def baixar_python():
    if PYTHON_ZIP.exists():
        log("  Python ZIP ja existe, pulando download.")
        return True
    log("  Baixando Python 3.8.10 embeddable...")
    try:
        urllib.request.urlretrieve(PYTHON_URL, PYTHON_ZIP)
        log("  OK")
        return True
    except Exception as e:
        log("  ERRO: {}".format(e))
        log("")
        log("  Baixe manualmente:")
        log("  " + PYTHON_URL)
        log("  Salve como: " + str(PYTHON_ZIP))
        return False


def extrair_python():
    if (PYTHON_DIR / "python.exe").exists():
        log("  Python ja extraido, pulando.")
        return True
    log("  Extraindo Python...")
    try:
        with zipfile.ZipFile(PYTHON_ZIP, 'r') as z:
            z.extractall(PYTHON_DIR)
        log("  OK")
        return True
    except Exception as e:
        log("  ERRO: {}".format(e))
        return False


def configurar_python():
    log("  Configurando Python embeddable...")
    pth_files = list(PYTHON_DIR.glob("python3*._pth"))
    if not pth_files:
        log("  ERRO: arquivo _pth nao encontrado")
        return False
    pth = pth_files[0]
    txt = pth.read_text(encoding="utf-8")
    txt = txt.replace("#import site", "import site")
    if "Lib/site-packages" not in txt:
        txt += "\nLib/site-packages\n"
    pth.write_text(txt, encoding="utf-8")
    log("  OK: " + pth.name)
    return True


def instalar_pacotes():
    log("  Instalando pacotes no Python embeddable...")
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--target", str(PKGS_DIR),
        "--no-warn-script-location",
        "flask",
        "pdfplumber==0.10.4",
        "pymupdf==1.23.8",
        "python-docx",
    ]
    try:
        subprocess.check_call(cmd)
        log("  OK")
        return True
    except Exception as e:
        log("  ERRO: {}".format(e))
        return False


def copiar_app():
    log("  Copiando arquivos do app...")
    APP_DIR.mkdir(parents=True, exist_ok=True)
    (APP_DIR / "templates").mkdir(exist_ok=True)

    arquivos = [
        "app.py", "memorial_parser.py", "quota.py",
        "licenca.py", "config.ini",
    ]
    for arq in arquivos:
        src = BASE / arq
        if src.exists():
            shutil.copy2(src, APP_DIR / arq)
        else:
            log("  AVISO: {} nao encontrado".format(arq))

    # templates
    src_html = BASE / "templates" / "index.html"
    if src_html.exists():
        shutil.copy2(src_html, APP_DIR / "templates" / "index.html")

    # keys.enc se existir (chaves de API criptografadas)
    keys = BASE / "keys.enc"
    if keys.exists():
        shutil.copy2(keys, APP_DIR / "keys.enc")
        log("  keys.enc incluido.")

    # licenca.key se existir (chave de licenca pre-ativada)
    lic = BASE / "licenca.key"
    if lic.exists():
        shutil.copy2(lic, APP_DIR / "licenca.key")
        log("  licenca.key incluido — colega nao precisara ativar.")

    log("  OK")


def criar_launchers():
    log("  Criando launchers...")

    # Launcher principal — sem janela preta
    bat = DESTINO / "MemoConverter.bat"
    bat.write_bytes(
        b"@echo off\r\n"
        b"cd /d \"%~dp0app\"\r\n"
        b"if exist \"..\\python\\pythonw.exe\" (\r\n"
        b"    start \"\" \"..\\python\\pythonw.exe\" app.py\r\n"
        b") else (\r\n"
        b"    start \"\" \"..\\python\\python.exe\" app.py\r\n"
        b")\r\n"
    )

    # Launcher com janela (para diagnostico)
    bat2 = DESTINO / "MemoConverter_diagnostico.bat"
    bat2.write_bytes(
        b"@echo off\r\n"
        b"cd /d \"%~dp0app\"\r\n"
        b"echo Iniciando MemoConverter...\r\n"
        b"\"..\\python\\python.exe\" app.py\r\n"
        b"pause\r\n"
    )

    # LEIA-ME
    leia = DESTINO / "LEIA-ME.txt"
    leia.write_bytes(
        "Demarca\r\n"
        "=======\r\n\r\n"
        "Para usar: clique duas vezes em MemoConverter.bat\r\n"
        "O navegador abrira automaticamente.\r\n\r\n"
        "Se nao abrir, aguarde 5 segundos e acesse:\r\n"
        "http://localhost:5050\r\n\r\n"
        "Em caso de erro: use MemoConverter_diagnostico.bat\r\n"
        "para ver a mensagem de erro.\r\n"
        .encode("utf-8")
    )

    log("  OK")


def zipar():
    log("  Gerando ZIP para distribuicao...")
    zip_path = BASE / "MemoConverter_Portatil.zip"
    try:
        if zip_path.exists():
            zip_path.unlink()
        shutil.make_archive(str(BASE / "MemoConverter_Portatil"), "zip", BASE, "MemoConverter_Portatil")
        size = zip_path.stat().st_size // (1024*1024)
        log("  OK: MemoConverter_Portatil.zip ({} MB)".format(size))
        return True
    except Exception as e:
        log("  AVISO: Nao foi possivel gerar o ZIP automaticamente.")
        log("  Compacte a pasta MemoConverter_Portatil\\ manualmente.")
        return False


def main():
    print()
    print("=" * 55)
    print("  MemoConverter — Preparar Kit Portatil")
    print("=" * 55)
    print()

    # Cria estrutura
    if DESTINO.exists():
        log("Removendo instalacao anterior...")
        shutil.rmtree(DESTINO)
    PYTHON_DIR.mkdir(parents=True, exist_ok=True)
    PKGS_DIR.mkdir(parents=True, exist_ok=True)

    etapas = [
        ("1/5 Baixando Python",        baixar_python),
        ("2/5 Extraindo Python",        extrair_python),
        ("3/5 Configurando Python",     configurar_python),
        ("4/5 Instalando pacotes",      instalar_pacotes),
        ("5/5 Montando pacote",         lambda: (copiar_app(), criar_launchers(), True)[-1]),
    ]

    for titulo, func in etapas:
        print("[{}]".format(titulo))
        if not func():
            print()
            print("ERRO na etapa: " + titulo)
            print("Corrija o erro e execute novamente.")
            input("Pressione Enter para sair...")
            sys.exit(1)
        print()

    zipar()

    print()
    print("=" * 55)
    print("  Pronto!")
    print()
    print("  Envie MemoConverter_Portatil.zip para o colega.")
    print("  Ele descompacta e clica em MemoConverter.bat.")
    print("  Sem instalar nada, sem terminal.")
    print("=" * 55)
    print()
    input("Pressione Enter para sair...")


if __name__ == "__main__":
    main()
