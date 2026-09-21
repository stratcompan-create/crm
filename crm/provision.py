"""Ativação de um CRM novo para um escritório/cliente.

Uso (dentro do bench, com o site já criado e o app crm instalado):

    CRM_BRAND_NAME="Escritório X" CRM_LOGO_PATH=/tmp/logo.png \
    bench --site cliente.com.br execute crm.provision.provision_from_env

Perfis (CRM_PROFILE): agencia | escritorio | escritorio_empresarial.
Também pode ser chamado direto: crm.provision.provision_client(brand_name=...).
Tudo é idempotente: rodar de novo apenas reaplica os padrões.
"""

import os

import frappe

LEGAL_AREAS = [
	"Administrativo",
	"Agrário",
	"Ambiental",
	"Bancário",
	"Civil",
	"Compliance",
	"Consumidor",
	"Contratos",
	"Criminal",
	"Digital e LGPD",
	"Eleitoral",
	"Empresarial",
	"Família e Sucessões",
	"Imobiliário",
	"Internacional",
	"Previdenciário",
	"Propriedade Intelectual",
	"Saúde",
	"Societário",
	"Trabalhista",
	"Tributário",
	"Outros",
]


def seed_legal_areas():
	"""Troca a lista padrão de setores (em inglês) pelas áreas do direito."""
	for area in LEGAL_AREAS:
		if not frappe.db.exists("CRM Industry", area):
			frappe.get_doc({"doctype": "CRM Industry", "industry": area}).insert(ignore_permissions=True)

	for name in frappe.get_all("CRM Industry", pluck="name"):
		if name in LEGAL_AREAS:
			continue
		for dt in ("CRM Lead", "CRM Deal", "CRM Organization"):
			frappe.db.sql(f"update `tab{dt}` set industry = NULL where industry = %s", name)
		frappe.delete_doc("CRM Industry", name, force=1, ignore_permissions=True)


def _attach_logo(path: str) -> str:
	from frappe.utils.file_manager import save_file

	with open(path, "rb") as f:
		content = f.read()
	file_doc = save_file(os.path.basename(path), content, "FCRM Settings", "FCRM Settings", is_private=0)
	return file_doc.file_url


RESET_BODY = """<p>Olá {{ first_name }},</p>
<p>Recebemos um pedido para criar uma nova senha de acesso. Clique no botão abaixo para escolher a nova senha:</p>
<p style="margin: 15px 0px;"><a href="{{ link }}" rel="nofollow" class="btn btn-primary">Criar nova senha</a></p>
<p>Se você não fez esse pedido, ignore este e-mail: nada será alterado.</p>
<p>Se o botão não funcionar, copie e cole este endereço no navegador:<br><a href="{{ link }}">{{ link }}</a></p>"""

WELCOME_BODY = """<p>Olá {{ first_name }},</p>
<p>Uma conta foi criada para você em <a href="{{ site_url }}">{{ site_url }}</a>.</p>
<p>Seu login é: <b>{{ user }}</b></p>
<p>Clique no botão abaixo para concluir o cadastro e definir a sua senha:</p>
<p style="margin: 15px 0px;"><a href="{{ link }}" rel="nofollow" class="btn btn-primary">Concluir cadastro</a></p>
<p>Se o botão não funcionar, copie e cole este endereço no navegador:<br><a href="{{ link }}">{{ link }}</a></p>"""


def ensure_email_templates():
	"""E-mails de senha e de boas-vindas em português (os padrões do Frappe saem em inglês)."""
	for name, subject, body in (
		("Redefinição de senha", "Redefinição de senha", RESET_BODY),
		("Boas-vindas ao CRM", "Bem-vindo! Conclua o seu cadastro", WELCOME_BODY),
	):
		if frappe.db.exists("Email Template", name):
			doc = frappe.get_doc("Email Template", name)
			doc.subject, doc.response, doc.use_html = subject, body, 1
			doc.save(ignore_permissions=True)
		else:
			frappe.get_doc(
				{"doctype": "Email Template", "name": name, "subject": subject, "response": body, "use_html": 1}
			).insert(ignore_permissions=True)
	frappe.db.set_single_value("System Settings", "reset_password_template", "Redefinição de senha")
	frappe.db.set_single_value("System Settings", "welcome_email_template", "Boas-vindas ao CRM")


def apply_regional_defaults():
	"""Real (R$), país e formato de números do Brasil. Sem isso o Frappe cai no padrão americano
	(dólar, 1,234.56) e os valores do Financeiro aparecem em US$."""
	if frappe.db.exists("Currency", "BRL"):
		frappe.db.set_value("Currency", "BRL", {"enabled": 1, "symbol": "R$"})
	frappe.db.set_default("currency", "BRL")
	frappe.db.set_single_value("System Settings", "country", "Brazil")
	frappe.db.set_single_value("System Settings", "number_format", "#.###,##")
	frappe.db.set_single_value("System Settings", "currency_precision", "2")
	# sem isso o Frappe usa outro fuso e os horários (agenda, resumo das 8h) saem deslocados
	frappe.db.set_single_value("System Settings", "time_zone", "America/Sao_Paulo")
	frappe.db.set_single_value("FCRM Settings", "currency", "BRL")


def provision_client(
	brand_name: str,
	logo_path: str | None = None,
	favicon_path: str | None = None,
	website_url: str | None = None,
	language: str = "pt-BR",
	timezone: str = "America/Sao_Paulo",
	country: str = "Brazil",
	currency: str = "BRL",
	profile: str = "agencia",
):
	frappe.flags.in_install = True

	if frappe.db.exists("Language", language):
		frappe.db.set_value("Language", language, "enabled", 1)

	settings = {
		"setup_complete": 1,
		"language": language,
		"time_zone": timezone,
		"country": country,
		"date_format": "dd/mm/yyyy",
		"number_format": "#.###,##",
	}
	for key, value in settings.items():
		frappe.db.set_single_value("System Settings", key, value)

	if frappe.db.exists("Currency", currency):
		frappe.db.set_value("Currency", currency, "enabled", 1)
		frappe.db.set_single_value("Global Defaults", "default_currency", currency)
		frappe.db.set_single_value("FCRM Settings", "currency", currency)

	frappe.db.set_single_value("FCRM Settings", "brand_name", brand_name)
	frappe.db.set_single_value("System Settings", "app_name", brand_name)
	frappe.db.set_single_value("Website Settings", "app_name", brand_name)
	ensure_email_templates()
	apply_regional_defaults()
	if website_url:
		frappe.db.set_single_value("FCRM Settings", "website_url", website_url)
	if logo_path:
		logo_url = _attach_logo(logo_path)
		frappe.db.set_single_value("FCRM Settings", "brand_logo", logo_url)
		if not favicon_path:
			frappe.db.set_single_value("FCRM Settings", "favicon", logo_url)
	if favicon_path:
		frappe.db.set_single_value("FCRM Settings", "favicon", _attach_logo(favicon_path))

	for user in frappe.get_all("User", filters={"user_type": "System User"}, pluck="name"):
		frappe.db.set_value("User", user, {"language": language, "time_zone": timezone}, update_modified=False)

	seed_legal_areas()
	apply_profile(profile)

	frappe.db.commit()
	frappe.clear_cache()
	print(f"CRM ativado para: {brand_name}")


COMPANY_FIELDS = [
	"organization",
	"website",
	"territory",
	"annual_revenue",
	"no_of_employees",
	"company_description",
]

# Em lead (prospecção) faturamento e nº de funcionários ainda não são conhecidos,
# então somem do lead e continuam no negócio/cliente.
LEAD_UNKNOWN = ["annual_revenue", "no_of_employees"]

# agencia: os leads são escritórios (B2B).
# escritorio: advogado que atende pessoa física — campos de empresa somem.
# escritorio_empresarial: advogado que atende empresas (tributário, empresarial):
#   mantém os dados de empresa (organização vira "Empresa").
PROFILES = {
	"agencia": {"hide": {"CRM Lead": LEAD_UNKNOWN}, "labels": {}},
	"escritorio": {
		"hide": {"CRM Lead": COMPANY_FIELDS, "CRM Deal": COMPANY_FIELDS},
		"labels": {"industry": "Área do Direito"},
	},
	"escritorio_empresarial": {
		"hide": {
			"CRM Lead": ["territory", "company_description", *LEAD_UNKNOWN],
			"CRM Deal": ["territory", "company_description"],
		},
		"labels": {"industry": "Área do Direito", "organization": "Empresa"},
	},
}

# Texto exibido por perfil. Só troca o rótulo na tela; os dados (mesmo doctype) são os mesmos.
PROFILE_TEXTS = {
	"agencia": {
		"Honorários": "Receitas",
		"Honorário": "Receita",
		"Tipo de Honorário": "Tipo de Receita",
		"Cliente / Deal": "Cliente / Negócio",
		"Fixo": "Projeto",
		"Êxito": "Performance",
		"Consultivo Mensal": "Mensalidade",
		"Por Ato": "Avulso",
		"Ainda não há Honorários cadastrados para gerar relatório.": "Ainda não há Receitas cadastradas para gerar relatório.",
		"Cadastre Honorários e Negócios pra a calculadora ter o que analisar.": "Cadastre Receitas e Negócios pra a calculadora ter o que analisar.",
		"Receita Real (honorários pagos)": "Receita Real (recebimentos pagos)",
		"Total Geral (todos os honorários cadastrados)": "Total Geral (todas as receitas cadastradas)",
	},
}


def get_profile() -> str:
	return frappe.db.get_default("crm_profile") or "agencia"


def profile_messages(profile: str | None = None) -> dict:
	return PROFILE_TEXTS.get(profile or get_profile(), {})


PROFILE_DOCTYPES = ("CRM Lead", "CRM Deal")


def _prune_layout(node, hide):
	if isinstance(node, list):
		kept = []
		for item in node:
			item = _prune_layout(item, hide)
			if item is not None:
				kept.append(item)
		return kept
	if isinstance(node, dict):
		if isinstance(node.get("fields"), list):
			node["fields"] = [f for f in node["fields"] if f not in hide]
			if not node["fields"]:
				return None
		if isinstance(node.get("columns"), list):
			node["columns"] = _prune_layout(node["columns"], hide)
			if not node["columns"]:
				return None
		if isinstance(node.get("sections"), list):
			node["sections"] = _prune_layout(node["sections"], hide)
	return node


def drop_hidden_fields(doctype: str, data: dict) -> dict:
	"""Tira das colunas/linhas padrão da lista os campos escondidos pelo perfil."""
	meta = frappe.get_meta(doctype)
	hidden = {f.fieldname for f in meta.fields if f.hidden}
	if not hidden:
		return data
	data["columns"] = [c for c in data["columns"] if c.get("key") not in hidden]
	data["rows"] = [r for r in data["rows"] if r not in hidden]
	return data


def apply_profile(profile: str):
	import json

	if profile not in PROFILES:
		frappe.throw(f"Perfil desconhecido: {profile}. Use: {', '.join(PROFILES)}")
	frappe.db.set_default("crm_profile", profile)
	hide_map = PROFILES[profile]["hide"]
	labels = PROFILES[profile]["labels"]

	def setter(dt, fieldname, prop, value, ptype):
		frappe.make_property_setter(
			{"doctype": dt, "fieldname": fieldname, "property": prop, "value": value, "property_type": ptype}
		)

	for dt in PROFILE_DOCTYPES + ("CRM Organization",):
		for fieldname, label in labels.items():
			if frappe.get_meta(dt).has_field(fieldname):
				setter(dt, fieldname, "label", label, "Data")

	for dt in PROFILE_DOCTYPES:
		hide = hide_map.get(dt, [])
		for fieldname in hide:
			setter(dt, fieldname, "hidden", "1", "Check")

		for layout_type in ("Quick Entry", "Side Panel", "Data Fields"):
			name = f"{dt}-{layout_type}"
			raw = frappe.db.get_value("CRM Fields Layout", name, "layout")
			if raw and hide:
				frappe.db.set_value(
					"CRM Fields Layout", name, "layout", json.dumps(_prune_layout(json.loads(raw), set(hide)))
				)

		qf = frappe.db.get_value("CRM Global Settings", {"dt": dt}, ["name", "json"], as_dict=True)
		if qf and qf.json and hide:
			kept = [f for f in json.loads(qf.json) if f not in hide]
			frappe.db.set_value("CRM Global Settings", qf.name, "json", json.dumps(kept))

	if profile in ("escritorio", "escritorio_empresarial"):
		# "Serviço" da receita passa a ser a área do direito
		setter("CRM Honorario", "servico", "options", "\n" + "\n".join(LEGAL_AREAS), "Text")

	frappe.clear_cache()


def provision_from_env():
	provision_client(
		brand_name=os.environ["CRM_BRAND_NAME"],
		logo_path=os.environ.get("CRM_LOGO_PATH") or None,
		favicon_path=os.environ.get("CRM_FAVICON_PATH") or None,
		website_url=os.environ.get("CRM_WEBSITE_URL") or None,
		profile=os.environ.get("CRM_PROFILE") or "agencia",
	)
