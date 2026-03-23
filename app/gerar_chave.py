# -*- coding: utf-8 -*-
"""
gerar_chave.py
Script para o ADMINISTRADOR gerar chaves de licenca.
Execute este script na SUA maquina. NAO distribua este arquivo.

Uso:
    python gerar_chave.py           -> gera chave para 6 meses
    python gerar_chave.py 12        -> gera chave para 12 meses
    python gerar_chave.py 3         -> gera chave para 3 meses
"""

import sys
from licenca import gerar_chave

meses = int(sys.argv[1]) if len(sys.argv) > 1 else 6

chave, validade = gerar_chave(meses)

print()
print("=" * 60)
print("  CHAVE DE LICENCA GERADA")
print("=" * 60)
print()
print("  Validade : {} ({} meses)".format(validade, meses))
print()
print("  Chave    :")
print()
print("  " + chave)
print()
print("=" * 60)
print()
print("Envie a chave acima para o usuario.")
print("Ele deve colar no app em: Licenca -> Inserir chave")
print()
