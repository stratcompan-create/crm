"""Teste de fumaça: Negócio ganho, cobrança, pós-venda, agendamento, painel e resumo semanal.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Cria dados de teste e limpa no fim.
"""

import frappe, json
from frappe.utils import add_days, nowdate, getdate
from datetime import datetime, timedelta
from crm.api import automacoes as au, agenda, saude


def run():
    frappe.set_user("Administrator")
    res=[]
    def ck(n,c,extra=""): res.append(bool(c)); print(("OK  " if c else "FAIL"), n, extra)
    made=[]
    try:
        cfg=au.get_config(); ck("config com padrões", cfg.cobranca_dias_antes==3 and "{nome}" in cfg.cobranca_mensagem)
        au.save_settings(json.dumps({"parcelas_padrao":3,"agenda_ativa":1,"agenda_responsavel":"Administrator"}))
        # 1. distribuição
        from frappe.utils import cint
        au.sync_lead_distribution()
        print("regra:", frappe.db.exists("Assignment Rule","Distribuição automática de leads"), "vendedores:", au._sellers())
        # 2. negócio ganho
        lead=frappe.get_doc({"doctype":"CRM Lead","first_name":"Zz Teste","last_name":"Auto","email":"zz.teste@example.com","lead_owner":"Administrator"}).insert(ignore_permissions=True); made.append(("CRM Lead",lead.name))
        deal=frappe.get_doc({"doctype":"CRM Deal","first_name":"Zz Teste","last_name":"Auto","email":"zz.teste@example.com","lead":lead.name,"deal_owner":"Administrator","deal_value":3000,"status":"Qualification","budget_items":[{"description":"Site institucional","qty":1,"unit_price":3000}]}).insert(ignore_permissions=True); made.append(("CRM Deal",deal.name))
        deal.status="Won"; deal.save(ignore_permissions=True)
        hs=frappe.get_all("CRM Honorario",filters={"deal":deal.name},fields=["name","valor","data_vencimento","parcelas"],order_by="data_vencimento asc")
        for h in hs: made.append(("CRM Honorario",h.name))
        ck("3 parcelas criadas", len(hs)==3 and abs(sum(h.valor for h in hs)-3000)<0.01, str([(str(h.data_vencimento),h.valor) for h in hs]))
        ck("contrato anexado", frappe.db.exists("File",{"attached_to_name":deal.name,"file_name":["like","Contrato v1%"]}))
        ck("tarefas de início", frappe.db.count("CRM Task",{"reference_doctype":"CRM Deal","reference_docname":deal.name})==3)
        ck("conta do cliente", frappe.db.exists("CRM Client Account",{"client_name":"Zz Teste Auto"}))
        for t in frappe.get_all("CRM Task",filters={"reference_docname":deal.name},pluck="name"): made.append(("CRM Task",t))
        # 3. cobrança
        h=hs[0]; frappe.db.set_value("CRM Honorario",h.name,"data_vencimento",add_days(nowdate(),3))
        n=au.send_billing_reminders()
        ck("lembrete 3 dias antes enviado", n>=1 and frappe.db.get_value("CRM Honorario",h.name,"lembretes_enviados")==1)
        ck("comunicação na linha do tempo", frappe.db.exists("Communication",{"reference_name":deal.name,"subject":["like","Lembrete de pagamento%"]}))
        ck("não repete no mesmo dia", au.send_billing_reminders()==0)
        frappe.db.set_value("CRM Honorario",hs[1].name,{"data_vencimento":add_days(nowdate(),-7),"status":"Atrasado"})
        ck("atraso de 7 dias cobra", au.send_billing_reminders()>=1)
        # 9. pós-venda
        frappe.db.set_value("CRM Deal",deal.name,"closed_date",add_days(nowdate(),-8))
        au.run_posvenda()
        ck("pós-venda: avaliação pedida", frappe.db.get_value("CRM Deal",deal.name,"posvenda_avaliacao_em") is not None)
        ck("pós-venda: indicação ainda não", frappe.db.get_value("CRM Deal",deal.name,"posvenda_indicacao_em") is None)
        # 4. agenda
        info=agenda.get_public_info(); ck("agenda com horários", info["ativa"] and len(info["dias"])>0)
        d0=info["dias"][0]; frappe.local.request_ip="127.0.0.1"
        r=agenda.book("Maria Teste","maria.teste@example.com","(87) 99999-0000",d0["data"],d0["horarios"][0],"quero um site")
        m=frappe.get_all("CRM Reuniao",filters={"email":"maria.teste@example.com"},pluck="name"); made+= [("CRM Reuniao",x) for x in m]
        ml=frappe.db.get_value("CRM Lead",{"email":"maria.teste@example.com"}); made.append(("CRM Lead",ml))
        ck("reunião criada + lead + tarefa", len(m)==1 and ml and frappe.db.exists("CRM Task",{"reference_docname":ml,"title":["like","%Maria Teste"]}), r["inicio"])
        for t in frappe.get_all("CRM Task",filters={"reference_docname":ml},pluck="name"): made.append(("CRM Task",t))
        info2=agenda.get_public_info(); ck("horário ocupado some", d0["horarios"][0] not in next((x["horarios"] for x in info2["dias"] if x["data"]==d0["data"]),[]))
        try: agenda.book("Outra","o@example.com","(87) 99999-0000",d0["data"],d0["horarios"][0]); ck("bloqueia horário duplicado",False)
        except Exception: ck("bloqueia horário duplicado",True)
        # 7. saúde + 11. relatório
        sv=saude.get_business_health(); ck("painel de saúde", len(sv["itens"])>=5, str([(i["key"],i["count"]) for i in sv["itens"]]))
        rep=au.build_weekly_report(); html=au._report_html(rep); ck("relatório semanal", "Resumo da semana" in html and rep["atrasado"]>=0)
    finally:
        frappe.db.rollback()
        for dt,n in reversed(made):
            try:
                if n and frappe.db.exists(dt,n): frappe.delete_doc(dt,n,force=True,ignore_permissions=True)
            except Exception as e: print("limpeza",dt,n,e)
        for x in frappe.get_all("Communication",filters={"subject":["like","%Lembrete de pagamento%"]},pluck="name")+frappe.get_all("Communication",filters={"subject":["like","Como foi trabalhar%"]},pluck="name"): frappe.delete_doc("Communication",x,force=True,ignore_permissions=True)
        for x in frappe.get_all("File",filters={"file_name":["like","Contrato v1 - Zz%"]},pluck="name"): frappe.delete_doc("File",x,force=True,ignore_permissions=True)
        for x in frappe.get_all("CRM Client Account",filters={"client_name":"Zz Teste Auto"},pluck="name"): frappe.delete_doc("CRM Client Account",x,force=True,ignore_permissions=True)
        frappe.db.sql("delete from `tabEmail Queue` where creation > now() - interval 1 hour")
        frappe.db.set_single_value("CRM Automacoes Config","parcelas_padrao",1); frappe.db.set_single_value("CRM Automacoes Config","agenda_ativa",0)
        frappe.db.commit()
    return res
