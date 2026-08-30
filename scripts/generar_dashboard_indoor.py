#!/usr/bin/env python3
"""generar_dashboard_indoor.py — Genera dashboard indoor desde planilla de cultivo.
Lee Google Sheets (Inventario + Registro Cultivo) y emite dashboard_web/index.html.
Renacido 29/8/2026 (el original se perdió con el disco)."""
import os, sys, json, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google_api import sheets_get

SHEET = "1X6wGVPj4WtlNNnglBwqzE5VWPEPMuMrRD4z6mxqA7nY"
OUT = os.environ.get("DASHBOARD_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_web", "index.html"))
FLORA_INICIO = datetime.date(2026, 8, 18)  # pase masivo vege→flora
DIAS_FLORA = 60  # ciclo de flora

def parse_fecha(s):
    try:
        return datetime.datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except Exception:
        return None

def main():
    r = sheets_get(SHEET, ["🌱 Inventario de Plantas!A1:L170"])
    rows = r["valueRanges"][0].get("values", [])
    data = [row for row in rows[1:] if row and any(c.strip() for c in row)]

    plantas = []
    for row in data:
        def cell(i):
            return row[i].strip() if i < len(row) and row[i].strip() else ""
        plantas.append({
            "id": cell(0), "genetica": cell(1), "tipo": cell(2),
            "fecha": cell(3), "ubicacion": cell(4), "fase": cell(5), "notas": cell(6),
        })

    total = len(plantas)
    flora = [p for p in plantas if p["fase"] == "Flora"]
    vege = [p for p in plantas if "Vege" in p["ubicacion"] and p["fase"] != "Flora" and p["fase"] != "Baja"]
    auto = [p for p in plantas if "Autom" in p["ubicacion"]]
    baja = [p for p in plantas if p["fase"] == "Baja"]

    # conteo por genética (flora)
    gen_counts = {}
    for p in flora:
        g = p["genetica"] or "Sin genética"
        gen_counts[g] = gen_counts.get(g, 0) + 1

    # registro cultivo: últimos riegos
    rr = sheets_get(SHEET, ["Registro Cultivo!A2:N1071"])
    regs = rr["valueRanges"][0].get("values", [])
    riegos = []
    for row in regs:
        if not row or not any(c.strip() for c in row):
            continue
        def cell(i):
            return row[i].strip() if i < len(row) and row[i].strip() else ""
        riegos.append({
            "id": cell(0), "fecha": cell(1), "fase": cell(2),
            "ec": cell(5), "ph": cell(4), "notas": cell(10),
        })
    riegos.sort(key=lambda x: parse_fecha(x["fecha"]) or datetime.date.min, reverse=True)
    ultimos_riegos = riegos[:8]

    hoy = datetime.date.today()
    dia_flora = (hoy - FLORA_INICIO).days + 1
    cosecha_est = FLORA_INICIO + datetime.timedelta(days=DIAS_FLORA)
    falta = (cosecha_est - hoy).days
    pct = min(100, round(dia_flora / DIAS_FLORA * 100))

    def esc(s):
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    gen_rows = "".join(
        f"<tr><td>{esc(g)}</td><td class='num'>{c}</td></tr>"
        for g, c in sorted(gen_counts.items(), key=lambda x: -x[1])
    )
    riego_rows = "".join(
        f"<tr><td>{esc(r['fecha'])}</td><td>{esc(r['id'])}</td><td>{esc(r['fase'])}</td>"
        f"<td class='num'>{esc(r['ph'])}</td><td class='num'>{esc(r['ec'])}</td><td>{esc(r['notas'][:60])}</td></tr>"
        for r in ultimos_riegos
    )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🌿 Dashboard Indoor — La Ronda</title>
<style>
:root {{ --verde:#0d2d1a; --dorado:#d29914; }}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#0f1a12; color:#e8e8e8; padding:20px; }}
h1 {{ color:var(--dorado); font-size:1.6rem; margin-bottom:4px; }}
.sub {{ color:#9aa; font-size:.85rem; margin-bottom:20px; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin-bottom:20px; }}
.card {{ background:#16281b; border:1px solid #2a4a33; border-radius:12px; padding:14px; text-align:center; }}
.card .n {{ font-size:1.8rem; font-weight:700; color:var(--dorado); }}
.card .l {{ font-size:.8rem; color:#aab; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
.panel {{ background:#16281b; border:1px solid #2a4a33; border-radius:12px; padding:16px; }}
.panel h2 {{ color:var(--dorado); font-size:1.05rem; margin-bottom:10px; }}
table {{ width:100%; border-collapse:collapse; font-size:.85rem; }}
th {{ text-align:left; color:#c8c8c8; border-bottom:1px solid #2a4a33; padding:4px 6px; }}
td {{ padding:4px 6px; border-bottom:1px solid #1f3626; }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.barra {{ background:#0a1510; border-radius:8px; height:14px; margin:8px 0; overflow:hidden; }}
.barra > div {{ background:linear-gradient(90deg,var(--verde),var(--dorado)); height:100%; }}
.alert {{ background:#3a2a10; border:1px solid var(--dorado); color:#ffd97a; padding:10px 14px; border-radius:10px; margin-bottom:16px; font-size:.9rem; }}
@media (max-width:700px) {{ .grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<h1>🌿 Dashboard Indoor — La Ronda</h1>
<div class="sub">Sede Catamarca 405 · Actualizado {hoy.strftime('%d/%m/%Y %H:%M')} · Pase a flora: 18/08/2026</div>

<div class="alert">⚠️ <b>Cosecha Sala Flora 08-09/08:</b> falta cargar pesos post-trim (altas/bajas → stock). Registro de cosechas pendiente.</div>

<div class="cards">
  <div class="card"><div class="n">{total}</div><div class="l">Plantas totales</div></div>
  <div class="card"><div class="n">{len(flora)}</div><div class="l">🌸 Sala Flora</div></div>
  <div class="card"><div class="n">{len(auto)}</div><div class="l">Sala C Automáticas</div></div>
  <div class="card"><div class="n">{len(vege)}</div><div class="l">Sala Vege</div></div>
  <div class="card"><div class="n">{len(baja)}</div><div class="l">Bajas</div></div>
  <div class="card"><div class="n">{dia_flora}</div><div class="l">Día de flora</div></div>
  <div class="card"><div class="n">{pct}%</div><div class="l">Ciclo flora</div></div>
  <div class="card"><div class="n">{falta}</div><div class="l">Días p/ cosecha ~{cosecha_est.strftime('%d/%m')}</div></div>
</div>

<div class="barra"><div style="width:{pct}%"></div></div>

<div class="grid">
  <div class="panel">
    <h2>🌸 Genéticas en Flora ({len(flora)} plantas)</h2>
    <table><tr><th>Genética</th><th class="num">Plantas</th></tr>{gen_rows}</table>
  </div>
  <div class="panel">
    <h2>💧 Últimos riegos / registros</h2>
    <table><tr><th>Fecha</th><th>ID</th><th>Fase</th><th class="num">pH</th><th class="num">EC</th><th>Notas</th></tr>{riego_rows}</table>
  </div>
</div>

<div class="sub" style="margin-top:16px">Clave de acceso: 2019 · Generado por Julia 🦞 · Planilla: 🌱 Planilla de Cultivo</div>
</body>
</html>"""

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(html)
    print("Dashboard generado:", OUT)
    print(f"  total={total} flora={len(flora)} auto={len(auto)} vege={len(vege)} baja={len(baja)}")
    print(f"  dia_flora={dia_flora} cosecha_est={cosecha_est} falta={falta} pct={pct}%")

if __name__ == "__main__":
    main()