# -*- coding: utf-8 -*-
"""
app.py - MemoConverter v1.7.0
Uso: python app.py  (ou duplo clique em iniciar.bat)
"""

import os, csv, json, tempfile, configparser, sys
from pathlib import Path

# Garante que a pasta do app.py esteja no sys.path
# Necessario para Python embeddable (portatil)
_APP_DIR = Path(__file__).parent.resolve()
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_file, after_this_request
from memorial_parser import (
    ler_pdf, ler_docx, extrair_vertices, extrair_meta,
    ocr_google_vision, ocr_google_vision_imagem, extrair_com_gemini,
    ordenar_vertices, validar_poligono, calcular_sentido
)
from quota import status_cota, registrar_uso, verificar_antes_ocr
from licenca import status_licenca, verificar_chave, salvar_chave

APP_VERSION = "1.7.0"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

# ── Senha embutida para descriptografar keys.enc ─────────
_KEYS_SENHA = "MemorialConverter#SPU@2024!keys"
_keys_cache = None


def _carregar_keys_enc():
    """
    Tenta ler chaves do keys.enc (criptografado).
    Retorna dict ou {} se nao existir.
    """
    global _keys_cache
    if _keys_cache is not None:
        return _keys_cache

    import base64, hashlib, json
    keys_path = Path(__file__).parent / "keys.enc"
    if not keys_path.exists():
        _keys_cache = {}
        return _keys_cache
    try:
        enc   = keys_path.read_bytes()
        chave = hashlib.sha256(_KEYS_SENHA.encode()).digest()
        dados = base64.b64decode(enc)
        dec   = bytearray(b ^ chave[i % len(chave)] for i, b in enumerate(dados))
        _keys_cache = json.loads(dec.decode("utf-8"))
    except Exception:
        _keys_cache = {}
    return _keys_cache


def _get_api_key(nome):
    """
    Retorna chave de API.
    Prioridade: keys.enc (criptografado) > config.ini (texto claro)
    """
    keys = _carregar_keys_enc()
    if keys.get(nome, "").strip():
        return keys[nome].strip()
    cfg = carregar_config()
    return cfg.get(nome, "api_key", fallback="").strip()


def carregar_config():
    cfg = configparser.ConfigParser()
    p   = Path(__file__).parent / "config.ini"
    if p.exists():
        cfg.read(p, encoding="utf-8")
    return cfg


def contar_paginas_pdf(path):
    """Conta paginas do PDF sem extrair texto."""
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return len(pdf.pages)
    except Exception:
        pass
    try:
        import fitz
        doc = fitz.open(path)
        n   = len(doc)
        doc.close()
        return n
    except Exception:
        pass
    return 1   # fallback conservador


# ── rotas ────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/processar", methods=["POST"])
def processar():
    cfg = carregar_config()

    if "arquivo" in request.files:
        f   = request.files["arquivo"]
        ext = Path(f.filename).suffix.lower()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        f.save(tmp.name); tmp.close()

        try:
            ocr_usado = False

            if ext == ".pdf":
                texto, status = ler_pdf(tmp.name)

                if status == "ocr_needed":
                    api_vision = _get_api_key("google_vision")

                    if not api_vision:
                        return jsonify({
                            "erro":       "pdf_escaneado",
                            "mensagem":   "Este PDF é escaneado. Configure a chave do Google Vision em ⚙ Configurar APIs."
                        }), 422

                    # verifica cota antes de chamar a API
                    n_pag = contar_paginas_pdf(tmp.name)
                    pode, msg_cota = verificar_antes_ocr(n_pag)
                    if not pode:
                        return jsonify({"erro": "cota_excedida", "mensagem": msg_cota}), 429

                    max_pag = cfg.getint("app", "max_paginas_ocr", fallback=20)
                    texto, err_ocr = ocr_google_vision(tmp.name, api_vision, min(n_pag, max_pag))

                    if err_ocr and not texto:
                        return jsonify({"erro": err_ocr}), 500

                    registrar_uso(n_pag)
                    ocr_usado = True

            elif ext in (".docx", ".doc"):
                texto, err = ler_docx(tmp.name)
                if err and not texto:
                    return jsonify({"erro": err}), 500

            elif ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff"):
                api_vision = _get_api_key("google_vision")
                if not api_vision:
                    return jsonify({
                        "erro":     "ocr_necessario",
                        "mensagem": "Imagens requerem Google Vision OCR. Configure a chave em ⚙ Configurar APIs."
                    }), 422

                pode, msg_cota = verificar_antes_ocr(1)
                if not pode:
                    return jsonify({"erro": "cota_excedida", "mensagem": msg_cota}), 429

                texto, err_ocr = ocr_google_vision_imagem(tmp.name, api_vision)
                if err_ocr and not texto:
                    return jsonify({"erro": err_ocr}), 500

                registrar_uso(1)
                ocr_usado = True

            else:
                return jsonify({"erro": "Formato nao suportado. Use PDF, Word (.docx) ou imagem (JPG, PNG)."}), 400

        finally:
            try: os.unlink(tmp.name)
            except: pass

    elif request.is_json:
        dados = request.get_json()
        texto = dados.get("texto", "").strip()
        ocr_usado = False
        if not texto:
            return jsonify({"erro": "Nenhum texto fornecido."}), 400
    else:
        return jsonify({"erro": "Envie um arquivo ou texto."}), 400

    vertices = extrair_vertices(texto)
    meta      = extrair_meta(texto)
    api_gemini = _get_api_key("gemini")

    sentido   = calcular_sentido(vertices) if len(vertices) >= 3 else None
    validacao = validar_poligono(vertices) if len(vertices) >= 3 else None

    return jsonify({
        "vertices":          vertices,
        "meta":              meta,
        "total":             len(vertices),
        "ocr_usado":         ocr_usado,
        "gemini_disponivel": bool(api_gemini),
        "texto":             texto,
        "sentido":           sentido,
        "validacao":         validacao,
    })


@app.route("/api/gemini", methods=["POST"])
def usar_gemini():
    cfg     = carregar_config()
    api_key  = _get_api_key("gemini")

    if not api_key:
        return jsonify({"erro": "Chave do Gemini nao configurada em config.ini ou keys.enc."}), 400

    dados   = request.get_json()
    texto   = (dados or {}).get("texto", "").strip()

    if not texto:
        return jsonify({"erro": "Texto nao fornecido."}), 400

    vertices, erro = extrair_com_gemini(texto, api_key)
    if erro:
        return jsonify({"erro": str(erro)}), 500

    if not isinstance(vertices, list):
        return jsonify({"erro": "Resposta inesperada do Gemini."}), 500

    return jsonify({"vertices": vertices, "total": len(vertices)})


@app.route("/api/exportar", methods=["POST"])
def exportar():
    dados    = request.get_json()
    vertices = dados.get("vertices", [])
    if not vertices:
        return jsonify({"erro": "Nenhum vertice para exportar."}), 400

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False,
        encoding="utf-8-sig", newline=""
    )
    writer = csv.writer(tmp, delimiter=";")
    writer.writerow(["Ponto", "X", "Y"])
    for v in vertices:
        # garante decimal com ponto (formato ArcGeek Topo)
        def fmt(val):
            try: return "{:.3f}".format(float(str(val).replace(",",".")))
            except: return str(val)
        writer.writerow([v.get("vertice",""), fmt(v.get("coord_e","")), fmt(v.get("coord_n",""))])
    tmp.close()

    @after_this_request
    def cleanup(response):
        try: os.unlink(tmp.name)
        except: pass
        return response

    return send_file(tmp.name, mimetype="text/csv", as_attachment=True,
                     download_name="vertices_memorial.csv")


@app.route("/api/versao", methods=["GET"])
def get_versao():
    return jsonify({"versao": APP_VERSION})


@app.route("/api/config", methods=["GET"])
def get_config():
    cfg = carregar_config()
    s   = status_cota()
    return jsonify({
        "google_vision": bool(_get_api_key("google_vision")),
        "gemini":        bool(_get_api_key("gemini")),
        "versao":        APP_VERSION,
        "cota": {
            "usadas":     s["usadas"],
            "limite":     s["limite"],
            "disponivel": s["disponivel"],
            "mes":        s["mes"],
            "bloqueado":  s["bloqueado"],
            "pct":        s["pct"],
        }
    })


@app.route("/api/config", methods=["POST"])
def set_config():
    dados    = request.get_json()
    cfg_path = Path(__file__).parent / "config.ini"
    cfg      = configparser.ConfigParser()
    if cfg_path.exists():
        cfg.read(cfg_path, encoding="utf-8")

    for sec in ("google_vision", "gemini", "app"):
        if not cfg.has_section(sec):
            cfg.add_section(sec)

    if "google_vision" in dados:
        cfg.set("google_vision", "api_key", dados["google_vision"])
    if "gemini" in dados:
        cfg.set("gemini", "api_key", dados["gemini"])
    if "limite_paginas_mes" in dados:
        cfg.set("google_vision", "limite_paginas_mes", str(int(dados["limite_paginas_mes"])))

    with open(cfg_path, "w", encoding="utf-8") as f:
        cfg.write(f)

    return jsonify({"ok": True})


@app.route("/api/licenca", methods=["GET"])
def get_licenca():
    return jsonify(status_licenca())


@app.route("/api/licenca", methods=["POST"])
def set_licenca():
    dados = request.get_json()
    chave = (dados or {}).get("chave", "").strip()
    if not chave:
        return jsonify({"erro": "Chave nao fornecida."}), 400
    valida, mensagem, validade = verificar_chave(chave)
    if valida:
        salvar_chave(chave)
    return jsonify({"valida": valida, "mensagem": mensagem, "validade": validade})


@app.route("/api/encerrar", methods=["POST"])
def encerrar():
    os._exit(0)


# ── inicializacao ─────────────────────────────────────────────

if __name__ == "__main__":
    import webbrowser, threading, socket

    cfg  = carregar_config()
    port = cfg.getint("app", "porta", fallback=5050)

    for p in range(port, port + 20):
        try:
            s = socket.socket(); s.bind(("127.0.0.1", p)); s.close()
            port = p; break
        except OSError:
            continue

    threading.Timer(1.2, webbrowser.open, args=["http://localhost:{}".format(port)]).start()
    print("\n  Memorial Converter v2 — http://localhost:{}\n".format(port))
    app.run(port=port, debug=False)
