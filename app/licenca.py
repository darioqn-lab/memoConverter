# -*- coding: utf-8 -*-
"""
licenca.py
Sistema de licenca por chave com validade.

Como funciona:
- A chave e uma string codificada em base64 contendo: validade + assinatura HMAC
- Sem um servidor externo — verificacao 100% local e offline
- O segredo (SECRET) deve ser mantido privado — quem souber o segredo
  pode gerar chaves. Troque o SECRET se precisar invalidar todas as chaves antigas.
"""

import hmac
import hashlib
import base64
import json
from datetime import datetime, date, timedelta
from pathlib import Path

# ── SEGREDO ──────────────────────────────────────────────────
# Troque por uma string aleatoria sua. Mantenha em sigilo.
# Se vazar, troque o segredo (todas as chaves antigas deixarao de funcionar).
SECRET = "MemorialConverter@SPU#2024$chave-privada"

# Arquivo onde a chave do usuario fica salva
CHAVE_PATH = Path(__file__).parent / "licenca.key"


# ── Geracao ──────────────────────────────────────────────────

def gerar_chave(meses=6):
    """
    Gera uma chave de licenca valida por N meses a partir de hoje.
    Retorna a chave como string.
    """
    validade = (date.today() + timedelta(days=30 * meses)).isoformat()
    payload  = json.dumps({"validade": validade}, separators=(",", ":"))
    payload_b64 = base64.b64encode(payload.encode()).decode()

    assinatura = hmac.new(
        SECRET.encode(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()[:16]   # 16 chars e suficiente

    chave = "{}.{}".format(payload_b64, assinatura)
    return chave, validade


# ── Verificacao ───────────────────────────────────────────────

def verificar_chave(chave):
    """
    Verifica se uma chave e valida e nao expirou.
    Retorna (valida: bool, mensagem: str, validade: str|None)
    """
    if not chave or "." not in chave:
        return False, "Chave invalida.", None

    partes = chave.strip().split(".")
    if len(partes) != 2:
        return False, "Formato de chave invalido.", None

    payload_b64, assinatura_recebida = partes

    # verifica assinatura
    assinatura_esperada = hmac.new(
        SECRET.encode(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()[:16]

    if not hmac.compare_digest(assinatura_recebida, assinatura_esperada):
        return False, "Chave invalida ou adulterada.", None

    # decodifica payload
    try:
        payload = json.loads(base64.b64decode(payload_b64).decode())
        validade_str = payload.get("validade", "")
        validade = date.fromisoformat(validade_str)
    except Exception:
        return False, "Chave com formato corrompido.", None

    hoje = date.today()
    if hoje > validade:
        dias = (hoje - validade).days
        return False, "Licenca expirada ha {} dia{}.".format(
            dias, "s" if dias != 1 else ""), validade_str

    dias_restantes = (validade - hoje).days
    return True, "Licenca valida por mais {} dia{}.".format(
        dias_restantes, "s" if dias_restantes != 1 else ""), validade_str


# ── Persistencia ──────────────────────────────────────────────

def ler_chave_salva():
    """Le a chave salva em licenca.key. Retorna string ou None."""
    if CHAVE_PATH.exists():
        return CHAVE_PATH.read_text(encoding="utf-8").strip()
    return None


def salvar_chave(chave):
    """Salva a chave em licenca.key."""
    CHAVE_PATH.write_text(chave.strip(), encoding="utf-8")


def status_licenca():
    """
    Retorna dict com status atual da licenca:
    { valida, mensagem, validade, dias_restantes, chave_presente }
    """
    chave = ler_chave_salva()
    if not chave:
        return {
            "valida":         False,
            "mensagem":       "Nenhuma chave de licenca encontrada.",
            "validade":       None,
            "dias_restantes": 0,
            "chave_presente": False,
        }

    valida, mensagem, validade_str = verificar_chave(chave)
    dias = 0
    if valida and validade_str:
        dias = (date.fromisoformat(validade_str) - date.today()).days

    return {
        "valida":         valida,
        "mensagem":       mensagem,
        "validade":       validade_str,
        "dias_restantes": dias,
        "chave_presente": True,
    }
