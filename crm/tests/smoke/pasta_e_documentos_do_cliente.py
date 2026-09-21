"""Teste de fumaça: Pasta do cliente, link de envio de documentos e anexos.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Cria dados de teste e limpa no fim.
"""

import frappe, json, io, types
from unittest import mock
from crm.api import clientes as c


def run():
    frappe.set_user("Administrator")
    res=[]
    def ck(n,x,e=""): res.append(bool(x)); print(("OK  " if x else "FAIL"),n,e)
    def _pdf():
        from pypdf import PdfWriter; w=PdfWriter(); w.add_blank_page(72,72); b=io.BytesIO(); w.write(b); return b.getvalue()
    def _jpeg():
        from PIL import Image; b=io.BytesIO(); Image.new('RGB',(40,40),(200,50,50)).save(b,'JPEG'); return b.getvalue()
    made=[]
    def up(token,item,name,data):
        up_=types.SimpleNamespace(filename=name,stream=io.BytesIO(data))
        with mock.patch.object(frappe,"request",types.SimpleNamespace(files={"file":up_}),create=True):
            return c.upload_public_document(token,item)
    try:
        d=frappe.get_doc({"doctype":"CRM Deal","organization_name":"Zz Walker Advocacia","first_name":"Walker","email":"walker@example.com","status":"Qualification"}).insert(ignore_permissions=True); made.append(("CRM Deal",d.name))
        pasta=frappe.db.get_value("CRM Deal",d.name,"pasta_cliente")
        ck("pasta do cliente criada ao criar o negócio", pasta=="Home/Clientes/Zz Walker Advocacia" and frappe.db.exists("File",pasta), pasta)
        ck("pasta raiz Clientes", frappe.db.exists("File","Home/Clientes"))
        d2=frappe.get_doc({"doctype":"CRM Deal","organization_name":"Zz Walker Advocacia","first_name":"Outro","status":"Qualification"}).insert(ignore_permissions=True); made.append(("CRM Deal",d2.name))
        ck("mesmo cliente compartilha a pasta", frappe.db.get_value("CRM Deal",d2.name,"pasta_cliente")==pasta)
        g=c.get_documents(d.name); ck("sugestão de itens", len(g["sugestao"])>=3, str(g["sugestao"]))
        r=c.create_request(d.name, json.dumps(["RG ou CNH","CPF"]), "Precisamos dos documentos"); token=r["link"].split("t=")[1]; made.append(("CRM Pedido Documentos",r["name"]))
        pub=c.get_public_request(token); ck("página pública lê o pedido", pub["nome"]=="Walker" and [i["nome"] for i in pub["itens"]]==["RG ou CNH","CPF"])
        out=up(token,"RG ou CNH","rg frente.jpg",__import__("io").BytesIO().getvalue() or _jpeg())
        ck("upload de foto vai para a pasta do cliente", out["ok"] and frappe.db.exists("File",{"folder":pasta,"attached_to_name":d.name}))
        f=frappe.get_all("File",filters={"folder":pasta,"is_folder":0},fields=["file_name","is_private"])
        ck("arquivo privado e nomeado pelo documento", f and f[0].is_private==1 and f[0].file_name.startswith("RG ou CNH - "), str(f))
        for bad,data,why in (("virus.exe",b"MZ"+b"0"*100,"tipo não aceito"),("falso.pdf",b"nao e pdf",  "conteúdo não confere")):
            try: up(token,"CPF",bad,data); ck("bloqueia "+why,False)
            except Exception: ck("bloqueia "+why,True)
        try: up(token,"Item que não foi pedido","a.pdf",b"%PDF-1.4 x"); ck("bloqueia item não pedido",False)
        except Exception: ck("bloqueia item não pedido",True)
        try: c.get_public_request("token-errado"); ck("link inválido recusado",False)
        except Exception: ck("link inválido recusado",True)
        pub2=c.get_public_request(token); ck("contador de enviados", [i["enviados"] for i in pub2["itens"]]==[1,0])
        c.close_request(r["name"])
        try: c.get_public_request(token); ck("link encerrado deixa de funcionar",False)
        except Exception: ck("link encerrado deixa de funcionar",True)
        # anexo feito na aba Anexos do negócio também vai para a pasta
        fa=frappe.get_doc({"doctype":"File","file_name":"contrato.pdf","attached_to_doctype":"CRM Deal","attached_to_name":d.name,"is_private":1,"content":_pdf()}).insert(ignore_permissions=True)
        ck("anexo do negócio é movido para a pasta", frappe.db.get_value("File",fa.name,"folder")==pasta, frappe.db.get_value("File",fa.name,"folder"))
        ck("get_documents lista tudo", len(c.get_documents(d.name)["arquivos"])>=2)
    finally:
        frappe.db.rollback()
        for f in frappe.get_all("File",filters={"folder":["like","Home/Clientes/Zz%"]},pluck="name"): frappe.delete_doc("File",f,force=True,ignore_permissions=True)
        for dt,n in reversed(made):
            if frappe.db.exists(dt,n):
                for cm in frappe.get_all("Comment",filters={"reference_name":n},pluck="name"): frappe.delete_doc("Comment",cm,force=True,ignore_permissions=True)
                frappe.delete_doc(dt,n,force=True,ignore_permissions=True)
        for f in ("Home/Clientes/Zz Walker Advocacia",):
            if frappe.db.exists("File",f): frappe.delete_doc("File",f,force=True,ignore_permissions=True)
        if frappe.db.exists("CRM Organization","Zz Walker Advocacia"): frappe.delete_doc("CRM Organization","Zz Walker Advocacia",force=True,ignore_permissions=True)
        frappe.db.commit()
    return res
