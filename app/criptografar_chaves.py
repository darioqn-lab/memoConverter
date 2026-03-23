# -*- coding: utf-8 -*-
"""
criptografar_chaves.py
Script para o ADMINISTRADOR criptografar as chaves de API.
Execute NA SUA MAQUINA. O arquivo keys.enc gerado vai dentro do pacote.

Uso:
    python criptografar_chaves.py
"""

import os
import sys
import json
import base64
import hashlib

# ── Chaves que voce quer proteger ──────────────────────────
# Preencha aqui antes de executar
CHAVES = {
    "google_vision": "SUA_CHAVE_GOOGLE_VISION_AQUI",
    "gemini":        "SUA_CHAVE_GEMINI_AQUI",
}

# ── Senha de criptografia ──────────────────────────────────
# Esta senha e embutida no app.py — nao e 100% inquebravel,
# mas impede leitura casual do keys.enc
SENHA = "MemorialConverter#SPU@2024!keys"


def criptografar(dados: dict, senha: str) -> bytes:
    """Criptografia simples com XOR + base64. Sem dependencias externas."""
    texto  = json.dumps(dados, ensure_ascii=False)
    # deriva chave de 32 bytes a partir da senha via SHA-256
    chave  = hashlib.sha256(senha.encode()).digest()
    # XOR ciclico
    result = bytearray()
    for i, byte in enumerate(texto.encode("utf-8")):
        result.append(byte ^ chave[i % len(chave)])
    return base64.b64encode(bytes(result))


def main():
    # filtra chaves vazias
    chaves_validas = {k: v for k, v in CHAVES.items()
                      if v and "AQUI" not in v}

    if not chaves_validas:
        print("\nERRO: Preencha as chaves no inicio do script antes de executar.")
        input("Pressione Enter para sair...")
        sys.exit(1)

    enc = criptografar(chaves_validas, SENHA)

    saida = os.path.join(os.path.dirname(__file__), "keys.enc")
    with open(saida, "wb") as f:
        f.write(enc)

    print()
    print("=" * 55)
    print("  Chaves criptografadas com sucesso!")
    print("=" * 55)
    print()
    for k in chaves_validas:
        print(f"  ✔ {k}")
    print()
    print(f"  Arquivo gerado: keys.enc")
    print()
    print("  Coloque o keys.enc dentro da pasta app/ do pacote")
    print("  distribuido para os colegas.")
    print()
    print("  NAO distribua este script (criptografar_chaves.py).")
    print("=" * 55)
    input("\nPressione Enter para sair...")


if __name__ == "__main__":
    main()
