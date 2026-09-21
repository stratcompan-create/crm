"""Teste de fumaça: Sugestões de resposta às mensagens do lead.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Cria dados de teste e limpa no fim.
"""

import frappe, json
from unittest import mock
from crm.api import sugestoes as s, ficha


def run():
    frappe.set_user("Administrator")
    res=[]
    def ck(n,c,e=""): res.append(bool(c)); print(("OK  " if c else "FAIL"),n,e)
    made=[]
    try:
        lead=frappe.get_doc({"doctype":"CRM Lead","first_name":"Maria","servico":"Sites","instagram_sender_id":"ZZ778"}).insert(ignore_permissions=True); made.append(lead.name)
        def msg(d,t): frappe.get_doc({"doctype":"CRM Instagram Message","lead":lead.name,"sender_id":"ZZ778","direction":d,"message":t,"timestamp":frappe.utils.now_datetime()}).insert(ignore_permissions=True)
        msg("Sent","Oi Maria, tudo bem? Vi seu perfil e...")
        msg("Received","Agradeço, mas com a loja nova estou sem caixa esse mês.")
        g=s.get_suggestions(lead.name)
        ck("modelos instantâneos + nada sob medida ainda", g["ativo"] and len(g["modelos"])==3 and g["sob_medida"]==[] and g["ia"]==False)
        ficha.save_ai_key("sk-ant-teste123")
        calls=[]
        def fake(*a,**k):
            calls.append(k["json"]["messages"][0]["content"])
            class R:
                ok=True; status_code=200
                def json(self): return {"content":[{"type":"text","text":json.dumps({"sugestoes":[{"titulo":"A","texto":"Entendo, Maria: loja nova pesa no caixa. O que ajudaria mais agora?"},{"titulo":"B","texto":"Posso te mostrar algo bem enxuto para o começo?"},{"titulo":"C","texto":"Sem pressa. Volto daqui a 60 dias?"}]})}]}
            return R()
        with mock.patch("requests.post",fake):
            a=s.generate_ai_suggestions(lead.name); b=s.generate_ai_suggestions(lead.name)
            ck("gera 3 sob medida", len(a["sugestoes"])==3 and a["sugestoes"][0]["origem"]=="ia")
            ck("segunda chamada usa o guardado (1 só chamada à IA)", len(calls)==1)
            ck("conversa e tema seguem para a IA", "loja nova" in calls[0] and "Preço ou orçamento" in calls[0])
            s.generate_ai_suggestions(lead.name, force=1); ck("'gerar outras' refaz", len(calls)==2)
        g2=s.get_suggestions(lead.name); ck("get_suggestions devolve o guardado", len(g2["sob_medida"])==3 and g2["ia"])
        msg("Sent","Entendo!"); msg("Received","Vou pensar e te falo")
        g3=s.get_suggestions(lead.name); ck("nova mensagem do lead: sugestões antigas não valem", g3["sob_medida"]==[] and g3["tema"]=="Vai pensar")
    finally:
        frappe.db.rollback()
        for n in made:
            for m in frappe.get_all("CRM Instagram Message",filters={"lead":n},pluck="name"): frappe.delete_doc("CRM Instagram Message",m,force=True,ignore_permissions=True)
            frappe.delete_doc("CRM Lead",n,force=True,ignore_permissions=True)
        frappe.db.set_single_value("CRM Automacoes Config","anthropic_api_key","")
        from frappe.utils.password import delete_all_passwords_for
        try: delete_all_passwords_for("CRM Automacoes Config","CRM Automacoes Config")
        except Exception: pass
        frappe.db.commit()
    return res
