"""Teste de fumaça: Boas-vindas e palavra-chave nos comentários do Instagram.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Cria dados de teste e limpa no fim.
"""

import frappe, json, uuid
U=uuid.uuid4().hex[:6]
from unittest import mock
from crm.api import instagram as ig, instagram_automacao as au


def run():
    frappe.set_user("Administrator")
    res=[]
    def ck(n,c): res.append(bool(c)); print(("OK  " if c else "FAIL"), n)
    sent=[]
    class R:
        ok=True; text="{}"
    def fake_post(url, params=None, json=None, timeout=None):
        sent.append(json); return R()
    S=frappe.get_single("CRM Instagram Settings")
    old=(S.enabled, S.boas_vindas_ativa)
    frappe.db.set_single_value("CRM Instagram Settings","enabled",1)
    frappe.db.set_single_value("CRM Instagram Settings","access_token","x")
    made=[]
    try:
        au.save_welcome(1,"Oi, {nome}! Bem-vindo.")
        au.save_gatilho("Escritório","Oi, {nome}! Aqui está o material.")
        with mock.patch("requests.post",fake_post), mock.patch.object(ig,"_fetch_sender_profile",lambda i:{"name":"Maria Souza","username":"maria.s"} if i=="T900" else {}):
            ev={"sender":{"id":"T900"},"message":{"text":"Oi"}}
            ig._process_message_event(ev)
            lead=frappe.db.get_value("CRM Lead",{"instagram_sender_id":"T900"}); made.append(lead)
            ck("boas-vindas enviada",len(sent)==1 and sent[0]["recipient"]=={"id":"T900"} and sent[0]["message"]["text"]=="Oi, Maria! Bem-vindo.")
            ck("boas-vindas registrada como Sent",frappe.db.count("CRM Instagram Message",{"lead":lead,"direction":"Sent"})==1)
            ig._process_message_event({"sender":{"id":"T900"},"message":{"text":"Segunda"}})
            ck("segunda mensagem não repete",len(sent)==1)
            sent.clear()
            au.process_comment_change({"id":"C1"+U,"text":"Quero o ESCRITORIO!","from":{"id":"T901","username":"joao.x"}})
            l2=frappe.db.get_value("CRM Lead",{"instagram_sender_id":"T901"}); made.append(l2)
            ck("comentário cria lead",bool(l2))
            ck("DM por comment_id",len(sent)==1 and sent[0]["recipient"]=={"comment_id":"C1"+U} and "Aqui está" in sent[0]["message"]["text"])
            print(frappe.db.get_value("CRM Lead",l2,["first_name","last_name"]), len(sent), sent); ck("nome cai no @ quando sem nome", frappe.db.get_value("CRM Lead",l2,"first_name")=="joao.x")
            au.process_comment_change({"id":"C1"+U,"text":"escritorio","from":{"id":"T901","username":"joao.x"}})
            au.process_comment_change({"id":"C2"+U,"text":"escritorio","from":{"id":"T901","username":"joao.x"}})
            print(frappe.cache().get_value("ig_comment_C1"+U), U); print(len(sent), [s["recipient"] for s in sent]); ck("sem duplicar (mesmo comentário / mesma pessoa)",len(sent)==1)
            au.process_comment_change({"id":"C3"+U,"text":"outro assunto","from":{"id":"T902","username":"z"}})
            print(len(sent), frappe.db.get_value("CRM Lead",{"instagram_sender_id":"T902"})); ck("sem palavra: ignora",len(sent)==1 and not frappe.db.get_value("CRM Lead",{"instagram_sender_id":"T902"}))
            # primeira msg depois de comentar não dá boas-vindas
            ig._process_message_event({"sender":{"id":"T901"},"message":{"text":"quero"}})
            ck("após gatilho sem boas-vindas",len(sent)==1)
            # webhook completo
            sent.clear()
            payload={"entry":[{"changes":[{"field":"comments","value":{"id":"C9"+U,"text":"escritório","from":{"id":"T903","username":"ana"}}}]}]}
            with mock.patch.object(frappe,"request",mock.Mock(method="POST",get_data=lambda:json.dumps(payload).encode()),create=True), mock.patch.object(frappe,"get_request_header",lambda *a:None):
                out=ig._handle_incoming_event()
            made.append(frappe.db.get_value("CRM Lead",{"instagram_sender_id":"T903"}))
            ck("webhook trata changes/comments",len(sent)==1 and out["status"]=="ok")
    finally:
        frappe.db.rollback()
        for l in made:
            if l:
                for m in frappe.get_all("CRM Instagram Message",filters={"lead":l},pluck="name"): frappe.delete_doc("CRM Instagram Message",m,force=True)
                frappe.delete_doc("CRM Lead",l,force=True,ignore_permissions=True)
        if frappe.db.exists("CRM Instagram Gatilho","Escritório"): frappe.delete_doc("CRM Instagram Gatilho","Escritório")
        frappe.db.set_single_value("CRM Instagram Settings","enabled",old[0]); frappe.db.set_single_value("CRM Instagram Settings","boas_vindas_ativa",0)
        frappe.db.commit()
    return res
