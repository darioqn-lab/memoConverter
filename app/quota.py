# -*- coding: utf-8 -*-
"""
quota.py
Controle de cota mensal do Google Vision.
Registra paginas consumidas no config.ini.
Bloqueia automaticamente quando atingir o limite configurado.
Zera o contador todo mes.
"""

import configparser
from datetime import datetime
from pathlib import Path


CFG_PATH = Path(__file__).parent / "config.ini"


def _ler_cfg():
    cfg = configparser.ConfigParser()
    if CFG_PATH.exists():
        cfg.read(CFG_PATH, encoding="utf-8")
    return cfg


def _salvar_cfg(cfg):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        cfg.write(f)


def status_cota():
    """
    Retorna dict com situacao atual da cota:
    {
      usadas: int,
      limite: int,
      disponivel: int,
      mes: str (YYYY-MM),
      bloqueado: bool,
      pct: float
    }
    """
    cfg    = _ler_cfg()
    limite = cfg.getint("google_vision", "limite_paginas_mes", fallback=1000)
    mes_ref = cfg.get("google_vision", "mes_referencia", fallback="").strip()
    usadas_str = cfg.get("google_vision", "paginas_usadas", fallback="").strip()

    mes_atual = datetime.now().strftime("%Y-%m")

    # zera contador se mudou o mes
    if mes_ref != mes_atual:
        usadas = 0
    else:
        try:
            usadas = int(usadas_str) if usadas_str else 0
        except ValueError:
            usadas = 0

    disponivel = max(0, limite - usadas)
    return {
        "usadas":     usadas,
        "limite":     limite,
        "disponivel": disponivel,
        "mes":        mes_atual,
        "bloqueado":  usadas >= limite,
        "pct":        round(usadas / limite * 100, 1) if limite > 0 else 0,
    }


def registrar_uso(paginas):
    """
    Registra consumo de N paginas no config.ini.
    Chame APOS uma chamada bem-sucedida ao Vision.
    """
    cfg     = _ler_cfg()
    mes_atual = datetime.now().strftime("%Y-%m")
    mes_ref   = cfg.get("google_vision", "mes_referencia", fallback="").strip()
    usadas_str = cfg.get("google_vision", "paginas_usadas", fallback="").strip()

    if mes_ref != mes_atual:
        usadas = 0
    else:
        try:
            usadas = int(usadas_str) if usadas_str else 0
        except ValueError:
            usadas = 0

    usadas += paginas

    if not cfg.has_section("google_vision"):
        cfg.add_section("google_vision")

    cfg.set("google_vision", "paginas_usadas", str(usadas))
    cfg.set("google_vision", "mes_referencia", mes_atual)
    _salvar_cfg(cfg)

    return usadas


def verificar_antes_ocr(n_paginas):
    """
    Verifica se ha cota suficiente para processar n_paginas.
    Retorna (pode_processar: bool, mensagem: str).
    """
    s = status_cota()

    if s["bloqueado"]:
        return False, (
            "Limite mensal de OCR atingido ({} de {} páginas usadas em {}).\n"
            "O limite será resetado automaticamente no próximo mês.\n"
            "Para aumentar o limite, edite 'limite_paginas_mes' no config.ini."
        ).format(s["usadas"], s["limite"], s["mes"])

    if n_paginas > s["disponivel"]:
        return False, (
            "Cota insuficiente: este PDF tem {} páginas mas restam apenas {} "
            "páginas disponíveis este mês ({} de {} usadas)."
        ).format(n_paginas, s["disponivel"], s["usadas"], s["limite"])

    return True, None
