"""Teste de fumaça: Mapas de estratégia: modelos, salvar e duplicar.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Cria dados de teste e limpa no fim.
"""

import frappe, json
from crm.api import mapas as m


def run():
    frappe.set_user("Administrator")
    res=[]
    def ck(n,x,e=""): res.append(bool(x)); print(("OK  " if x else "FAIL"),n,e)
    made=[]
    try:
        ck("5 modelos", len(m.get_templates())==6)
        for k in m.TEMPLATES:
            r=m.create_map("", k); made.append(r["name"]); g=m.get_map(r["name"])
            n=g["dados"]["nodes"]; e=g["dados"]["edges"]; ids={x["id"] for x in n}
            ck(f"modelo {k}: nós e ligações coerentes", n and all(x["source"] in ids and x["target"] in ids for x in e) and all(x["data"]["label"] for x in n), f"{len(n)} nós/{len(e)} ligações")
        r=m.create_map("Meu funil","funil"); made.append(r["name"])
        g=m.get_map(r["name"]); g["dados"]["nodes"].append({"id":"x1","type":"card","position":{"x":0,"y":0},"data":{"label":"Novo","icon":"star","color":"red","note":""}})
        m.save_map(r["name"], json.dumps(g["dados"]), "Funil da Walker")
        g2=m.get_map(r["name"]); ck("salvar e reabrir", len(g2["dados"]["nodes"])==7 and g2["titulo"]=="Funil da Walker")
        d2=m.duplicate_map(r["name"]); made.append(d2["name"]); ck("duplicar", m.get_map(d2["name"])["titulo"].endswith("(cópia)"))
        ck("lista", len(m.list_maps())>=6)
        try: m.save_map(r["name"], json.dumps({"nodes":[{"id":"a","data":{"label":"x"*1200000}}],"edges":[]})); ck("recusa mapa gigante",False)
        except Exception: ck("recusa mapa gigante",True)
    finally:
        frappe.db.rollback()
        for n in made:
            if frappe.db.exists("CRM Mapa",n): frappe.delete_doc("CRM Mapa",n,force=True,ignore_permissions=True)
        frappe.db.commit()
    return res
