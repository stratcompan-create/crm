"""Teste de fumaça: cópia de segurança noturna no Google Drive (sem falar com o Google).

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

import os
import tempfile
import types
from unittest import mock

import frappe

from crm.api import gdrive
from crm.api import saude_sistema as ss


def run():
    frappe.set_user("Administrator")
    res = []

    def ck(name, cond, extra=""):
        res.append(bool(cond))
        print("OK  " if cond else "FAIL", name, extra)

    saved = {k: frappe.db.get_default(k) for k in (gdrive.KEY_ON, gdrive.KEY_LAST_OK, gdrive.KEY_STATUS)}
    tmp = tempfile.mkdtemp()
    paths = []
    for name, size in (("db.sql.gz", 100), ("files.tar", 300), ("private-files.tar", 200)):
        p = os.path.join(tmp, name)
        with open(p, "wb") as f:
            f.write(b"x" * size)
        paths.append(p)
    uploads, deleted = [], []
    folders = [{"id": f"f{i}", "name": f"2026-09-{30 - i:02d}"} for i in range(12)]
    try:
        with mock.patch.object(gdrive, "is_connected", lambda: True), \
                mock.patch.object(gdrive, "_make_backup_files", lambda: paths), \
                mock.patch.object(gdrive, "_folder_for", lambda p: "rootid"), \
                mock.patch.object(gdrive, "_find_or_create_folder", lambda n, parent: "dayid"), \
                mock.patch.object(gdrive, "_resumable_upload", lambda path, name, parent: uploads.append((name, parent))), \
                mock.patch.object(gdrive, "_backup_children", lambda parent: folders), \
                mock.patch.object(gdrive, "_delete_drive_item", lambda i: deleted.append(i)):
            frappe.db.set_default(gdrive.KEY_ON, "1")
            gdrive.daily_backup()
            st = gdrive.get_backup_status()
            ck("cópia envia banco, arquivos e arquivos privados (sem a configuração do servidor)", [u[0] for u in uploads] == ["db.sql.gz", "files.tar", "private-files.tar"] and all(u[1] == "dayid" for u in uploads))
            ck("guarda só as 10 últimas (apaga as 2 mais antigas)", deleted == ["f10", "f11"], str(deleted))
            ck("status registra sucesso e tamanho", st["status"] == "ok" and st["ultimo_ok"] and st["tamanho_mb"] >= 0)

            uploads.clear()
            gdrive.set_backup_enabled(0)
            gdrive.daily_backup()
            ck("cópia desligada não envia nada", not uploads)
            gdrive.set_backup_enabled(1)

            with mock.patch.object(gdrive, "_resumable_upload", mock.Mock(side_effect=Exception("falha simulada"))):
                gdrive.daily_backup()
            ck("falha no envio é registrada como erro", gdrive.get_backup_status()["status"] == "erro")
            problem = [i for i in ss.run_checks() if i["key"] == "backup_drive"][0]
            ck("saúde do sistema avisa da falha da cópia", not problem["ok"])

        # envio em partes: cabeçalhos corretos e continua até o fim
        big = os.path.join(tmp, "grande.bin")
        with open(big, "wb") as f:
            f.write(b"y" * 25)
        calls = []

        def fake_put(url, headers=None, data=None, timeout=None):
            calls.append(headers["Content-Range"])
            return types.SimpleNamespace(status_code=200 if len(calls) == 3 else 308, text="")

        init = types.SimpleNamespace(status_code=200, headers={"Location": "https://upload/session"}, text="")
        with mock.patch.object(gdrive, "_headers", lambda: {"Authorization": "Bearer x"}), \
                mock.patch("requests.post", lambda *a, **k: init), mock.patch("requests.put", fake_put), \
                mock.patch.object(gdrive, "BACKUP_CHUNK", 10):
            gdrive._resumable_upload(big, "grande.bin", "dayid")
        ck("envio em partes usa os intervalos certos", calls == ["bytes 0-9/25", "bytes 10-19/25", "bytes 20-24/25"], str(calls))
    finally:
        frappe.db.rollback()
        for k, v in saved.items():
            if v is None:
                frappe.db.sql("delete from `tabDefaultValue` where defkey=%s and parent='__default'", (k,))
            else:
                frappe.db.set_default(k, v)
        frappe.db.commit()
    return res