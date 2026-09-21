"""Teste de fumaça: Ficha da reunião (com IA simulada) e preenchimento da proposta.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Cria dados de teste e limpa no fim.
"""

import frappe, json
from unittest import mock
from crm.api import ficha


def run():
    frappe.set_user("Administrator")
    res=[]
    def ck(n,c,e=""): res.append(bool(c)); print(("OK  " if c else "FAIL"),n,e)
    made=[]
    try:
        ficha.save_ai_key("sk-ant-teste123")
        lead=frappe.get_doc({"doctype":"CRM Lead","first_name":"Zz Ficha2","servico":"Sites"}).insert(ignore_permissions=True); made.append(("CRM Lead",lead.name))
        ans={"dor_objetivo":"Perdem clientes por demora","alinhado":"Site novo e CRM","escopo":"- Site\n- CRM","prazo":"60 dias","valor":"","objecoes":"","proximos":"Enviar proposta",
             "proposta":{"intro_texto":"Projeto de site e CRM para o escritório.","diagnostico_texto":"Leads se perdem por falta de retorno rápido.","diagnostico_cartoes":[{"titulo":"Demora","texto":"Resposta em dias"},{"titulo":"Sem controle","texto":"Planilhas soltas"}],
                         "escopo_itens":[{"titulo":"Site institucional","texto":"5 páginas"},{"titulo":"CRM","texto":"Funil e follow-up"}],"cronograma_etapas":[{"marco":"Semana 1-2","titulo":"Design","texto":"Layout aprovado"}],"cronograma_nota":"Entrega em 60 dias","preco":"R$ 99"}}
        class R:
            ok=True; status_code=200
            def json(self): return {"content":[{"type":"text","text":json.dumps(ans)}]}
        with mock.patch("requests.post",lambda *a,**k: R()):
            out=ficha.fill_from_transcript("CRM Lead",lead.name,"x"*200)
        ck("lead: ficha + rascunho guardado", frappe.db.get_value("CRM Lead",lead.name,"ficha") and "_proposta" in json.loads(frappe.db.get_value("CRM Lead",lead.name,"ficha")))
        ck("rascunho descarta campos fora do modelo (preço inventado)", "preco" not in json.loads(frappe.db.get_value("CRM Lead",lead.name,"ficha"))["_proposta"])
        r=frappe.get_doc("CRM Lead",lead.name).convert_to_deal()
        deal=frappe.get_doc("CRM Deal",r if isinstance(r,str) else r.name); made.append(("CRM Deal",deal.name))
        p=json.loads(frappe.db.get_value("CRM Deal",deal.name,"proposal_data") or "{}")
        ck("converter em negócio já preenche a proposta", p.get("intro",{}).get("texto","").startswith("Projeto") and len(p["escopo"]["itens"])==2 and len(p["diagnostico"]["cartoes"])==2 and p["cronograma"]["etapas"][0]["titulo"]=="Design", str(list(p)))
        ck("cronograma com nota do prazo", "60 dias" in p["cronograma"]["nota"])
        # edição manual no negócio não apaga o que o usuário já escreveu na proposta
        p["intro"]["texto"]="Texto meu"; frappe.db.set_value("CRM Deal",deal.name,"proposal_data",json.dumps(p))
        ficha.save_ficha("CRM Deal",deal.name,json.dumps({"alinhado":"outro alinhamento"}))
        p2=json.loads(frappe.db.get_value("CRM Deal",deal.name,"proposal_data"))
        ck("não sobrescreve texto já escrito na proposta", p2["intro"]["texto"]=="Texto meu")
        ck("rascunho preservado ao editar a ficha à mão", "_proposta" in json.loads(frappe.db.get_value("CRM Deal",deal.name,"ficha")))
    finally:
        frappe.db.rollback()
        for dt,n in reversed(made):
            if frappe.db.exists(dt,n):
                for c in frappe.get_all("Comment",filters={"reference_name":n},pluck="name"): frappe.delete_doc("Comment",c,force=True,ignore_permissions=True)
                frappe.delete_doc(dt,n,force=True,ignore_permissions=True)
        frappe.db.set_single_value("CRM Automacoes Config","anthropic_api_key","")
        from frappe.utils.password import delete_all_passwords_for
        try: delete_all_passwords_for("CRM Automacoes Config","CRM Automacoes Config")
        except Exception: pass
        frappe.db.commit()
    return res
