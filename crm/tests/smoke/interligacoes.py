"""Teste de fumaça: Ligações entre agenda, Prospecção, objeções, abordagem e proposta.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Cria dados de teste e limpa no fim.
"""

import frappe, json, types
from unittest import mock
from frappe.utils import nowdate, add_days, now_datetime, get_datetime
from crm.api import agenda, automacoes as au, instagram as ig, prospeccao, followup, proposta, sugestoes


def run():
    frappe.set_user("Administrator")
    res=[]
    def ck(n,x,e=""): res.append(bool(x)); print(("OK  " if x else "FAIL"),n,e)
    made=[]
    try:
        # ---- agendamento -> calendário + status + prospecção
        au.save_settings(json.dumps({"agenda_ativa":1,"agenda_responsavel":"Administrator"}))
        info=agenda.get_public_info(); d0=info["dias"][0]; frappe.local.request_ip="127.0.0.9"
        r=agenda.book("Zz Cliente Ponta","zz.ponta@example.com","(87) 98888-7777",d0["data"],d0["horarios"][1],"quero site")
        lead=frappe.db.get_value("CRM Lead",{"email":"zz.ponta@example.com"}); made.append(("CRM Lead",lead))
        reu=frappe.get_all("CRM Reuniao",filters={"lead":lead},pluck="name"); made+= [("CRM Reuniao",x) for x in reu]
        ev=frappe.get_all("Event",filters={"subject":["like","%Zz Cliente Ponta"]},pluck="name"); made+= [("Event",x) for x in ev]
        ck("reunião online vira evento no Calendário", len(ev)==1)
        ck("lead avança para Contatado", frappe.db.get_value("CRM Lead",lead,"status")=="Contacted")
        auto=prospeccao._automatic(add_days(nowdate(),-1))
        ck("Prospecção conta a reunião marcada sozinha", auto.get(nowdate(),{}).get("agendadas",0)>=1, str(auto.get(nowdate())))
        # ---- tarefa concluída -> reunião realizada + tarefa da ficha
        task=frappe.get_all("CRM Task",filters={"reference_docname":lead,"title":["like","%Zz Cliente Ponta"]},pluck="name")[0]; made.append(("CRM Task",task))
        t=frappe.get_doc("CRM Task",task); t.status="Done"; t.save(ignore_permissions=True)
        ck("concluir a tarefa marca reunião como realizada", frappe.db.get_value("CRM Reuniao",reu[0],"status")=="Realizada")
        ft=frappe.get_all("CRM Task",filters={"reference_docname":lead,"title":["like","Preencher a ficha%"]},pluck="name"); made+=[("CRM Task",x) for x in ft]
        ck("cria a tarefa de preencher a ficha", len(ft)==1)
        ck("Prospecção conta a reunião realizada", prospeccao._automatic(add_days(nowdate(),-1)).get(str(get_datetime(d0["data"]+" "+d0["horarios"][1]).date()),{}).get("realizadas",0)>=1)
        # ---- objeção numa mensagem -> prospecção + ficha + status
        l2=frappe.get_doc({"doctype":"CRM Lead","first_name":"Zz Obj","instagram_sender_id":"ZZOBJ1"}).insert(ignore_permissions=True); made.append(("CRM Lead",l2.name))
        before=json.loads(frappe.db.get_value("CRM Prospecao Dia",nowdate(),"objecoes") or "{}") if frappe.db.exists("CRM Prospecao Dia",nowdate()) else {}
        sugestoes.on_inbound_message(l2.name,"Agradeço, mas estou sem caixa esse mês")
        after=json.loads(frappe.db.get_value("CRM Prospecao Dia",nowdate(),"objecoes") or "{}")
        ck("objeção conta na Prospecção", after.get("Preço ou orçamento",0)==before.get("Preço ou orçamento",0)+1, str(after))
        ck("objeção entra na ficha do lead", "Preço ou orçamento" in json.loads(frappe.db.get_value("CRM Lead",l2.name,"ficha"))["objecoes"])
        ck("lead que respondeu sai de 'Novo'", frappe.db.get_value("CRM Lead",l2.name,"status")=="Contacted")
        ck("objeção entra na lista da Prospecção", "Preço ou orçamento" in (frappe.get_single("CRM Prospecao Config").objecoes or ""))
        # ---- abordagem -> serviço
        with mock.patch.object(frappe,"has_permission",lambda *a,**k:True):
            followup.ensure_defaults(); rr=followup.register_approach("Zz Abordado","Instagram","Site","zz_abordado")
        l3=rr["lead"]; made.append(("CRM Lead",l3))
        ck("abordagem 'Site' já define o serviço 'Sites'", frappe.db.get_value("CRM Lead",l3,"servico")=="Sites")
        ck("abordagem conta em Prospecção sem duplicar", prospeccao._effective_days(nowdate(),nowdate())[nowdate()]["abordados"]>=1)
        # ---- palavra-chave -> serviço
        if not frappe.db.exists("CRM Instagram Gatilho","zzcta"): frappe.get_doc({"doctype":"CRM Instagram Gatilho","palavra":"zzcta","mensagem":"Oi {nome}","servico":"CRM Jurídico"}).insert(ignore_permissions=True)
        made.append(("CRM Instagram Gatilho","zzcta"))
        from crm.api import instagram_automacao as ia
        frappe.db.set_single_value("CRM Instagram Settings","enabled",1)
        with mock.patch("requests.post",lambda *a,**k: types.SimpleNamespace(ok=True,text="")), mock.patch.object(ig,"_fetch_sender_profile",lambda i:{}):
            ia.process_comment_change({"id":"ZZC"+nowdate().replace("-","")+"x1","text":"zzcta","from":{"id":"ZZCM1","username":"zz.comenta"}})
        l4=frappe.db.get_value("CRM Lead",{"instagram_sender_id":"ZZCM1"}); made.append(("CRM Lead",l4))
        ck("palavra-chave já marca o serviço do lead", frappe.db.get_value("CRM Lead",l4,"servico")=="CRM Jurídico")
        # ---- proposta enviada -> etapa do negócio
        d=frappe.get_doc({"doctype":"CRM Deal","organization_name":"Zz Ponta Org","first_name":"Zz","status":"Qualification"}).insert(ignore_permissions=True); made.append(("CRM Deal",d.name))
        proposta._advance_to_proposal(d.name)
        ck("proposta enviada leva o negócio para 'Proposta'", frappe.db.get_value("CRM Deal",d.name,"status")=="Proposal/Quotation")
        frappe.db.set_value("CRM Deal",d.name,"status","Negotiation"); proposta._advance_to_proposal(d.name)
        ck("não volta etapa se já estava adiante", frappe.db.get_value("CRM Deal",d.name,"status")=="Negotiation")
    finally:
        frappe.db.rollback()
        frappe.db.set_single_value("CRM Automacoes Config","agenda_ativa",0); frappe.db.set_single_value("CRM Instagram Settings","enabled",0)
        for dt,n in reversed(made):
            if n and frappe.db.exists(dt,n):
                for dt2,f in (("CRM Task","reference_docname"),("Comment","reference_name"),("CRM Instagram Message","lead"),("CRM Reuniao","lead")):
                    for x in frappe.get_all(dt2,filters={f:n},pluck="name"): frappe.delete_doc(dt2,x,force=True,ignore_permissions=True)
                for f in frappe.get_all("File",filters={"attached_to_name":n},pluck="name"): frappe.delete_doc("File",f,force=True,ignore_permissions=True)
                try: frappe.delete_doc(dt,n,force=True,ignore_permissions=True)
                except Exception as e: print("limp",dt,n,str(e)[:60])
        for f in frappe.get_all("File",filters={"folder":["like","Home/Clientes/Zz%"]},pluck="name"): frappe.delete_doc("File",f,force=True,ignore_permissions=True)
        for f in ("Home/Clientes/Zz Ponta Org",):
            if frappe.db.exists("File",f): frappe.delete_doc("File",f,force=True,ignore_permissions=True)
        if frappe.db.exists("CRM Organization","Zz Ponta Org"): frappe.delete_doc("CRM Organization","Zz Ponta Org",force=True,ignore_permissions=True)
        cfg=frappe.get_single("CRM Prospecao Config"); frappe.db.set_single_value("CRM Prospecao Config","objecoes","\n".join(x for x in (cfg.objecoes or "").split("\n") if x.strip() and x!="Preço ou orçamento"))
        if frappe.db.exists("CRM Prospecao Dia",nowdate()): 
            o=json.loads(frappe.db.get_value("CRM Prospecao Dia",nowdate(),"objecoes") or "{}"); o.pop("Preço ou orçamento",None); frappe.db.set_value("CRM Prospecao Dia",nowdate(),"objecoes",json.dumps(o))
        frappe.db.commit()
    return res
