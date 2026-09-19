import frappe
from frappe import _
from frappe.utils import get_datetime
from frappe.utils.pdf import get_pdf

from crm.api import proposta
from crm.api.proposta import _valid_color

DOC_TITLES = {
	"orcamento": "Orçamento",
	"proposta": "Proposta Comercial",
	"contrato": "Contrato",
}


def build_document(deal: str, doc_type: str = "orcamento"):
	"""Render the deal's budget items as a PDF, titled according to doc_type.

	Kept intentionally generic: real per-office letterhead/branding pulls from
	FCRM Settings, but the Contrato body is a placeholder section, not real
	legal clause text — that has to be filled in per office/jurisdiction, not
	invented here.
	"""
	if doc_type not in DOC_TITLES:
		frappe.throw(_("Tipo de documento inválido: {0}").format(doc_type))

	if not frappe.db.exists("CRM Deal", deal):
		frappe.throw(_("Reference document {0} {1} does not exist.").format("CRM Deal", deal), frappe.DoesNotExistError)

	deal_doc = frappe.get_doc("CRM Deal", deal)
	if not deal_doc.has_permission("read"):
		frappe.throw(
			_("Not permitted to access reference document {0} {1}.").format("CRM Deal", deal),
			frappe.PermissionError,
		)

	settings = frappe.get_single("FCRM Settings")

	items = deal_doc.get("budget_items") or []
	subtotal = sum(flt(item.qty) * flt(item.unit_price) for item in items)
	discount = flt(deal_doc.get("budget_discount"))
	total = subtotal - discount

	client_name = _get_client_name(deal_doc)

	color = _valid_color(settings.get("brand_color"), "#042d3c")

	if doc_type == "proposta":
		data = proposta.get_proposal(deal)
		logo = ""
		if deal_doc.get("organization"):
			logo = frappe.db.get_value("CRM Organization", deal_doc.organization, "organization_logo") or ""
		html = proposta.render_proposal_html(deal_doc, settings, items, total, client_name, data, logo)
		proposta.create_followup_task(deal_doc, data, client_name)
		pdf_content = proposta.render_pdf(html)
	else:
		html = _build_html(
			doc_type=doc_type,
			brand_name=settings.get("brand_name") or "",
			client_name=client_name,
			deal_name=deal_doc.name,
			items=items,
			subtotal=subtotal,
			discount=discount,
			total=total,
			color=color,
		)
		pdf_content = get_pdf(html)

	return f"{DOC_TITLES[doc_type]} - {client_name}.pdf", pdf_content, deal_doc


@frappe.whitelist()
def generate_document(deal: str, doc_type: str = "orcamento"):
	"""Baixa o documento (orçamento, proposta comercial ou contrato) em PDF."""
	filename, pdf_content, _deal_doc = build_document(deal, doc_type)
	frappe.response["filename"] = filename
	frappe.response["filecontent"] = pdf_content
	frappe.response["type"] = "download"


def flt(value):
	try:
		return float(value or 0)
	except (TypeError, ValueError):
		return 0.0


def _get_client_name(deal_doc):
	if deal_doc.get("organization"):
		return deal_doc.get("organization")
	contacts = deal_doc.get("contacts") or []
	for contact in contacts:
		if contact.get("is_primary"):
			return contact.get("full_name") or contact.get("mobile_no") or deal_doc.name
	return deal_doc.get("lead_name") or deal_doc.name


def _fmt_currency(value):
	# Simple pt-BR style formatting (R$ 1.234,56) without depending on the
	# site's configured currency/locale settings.
	formatted = f"{value:,.2f}"
	formatted = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
	return f"R$ {formatted}"


def _build_html(doc_type, brand_name, client_name, deal_name, items, subtotal, discount, total, color="#042d3c"):
	title = DOC_TITLES[doc_type]
	today = get_datetime().strftime("%d/%m/%Y")

	rows_html = ""
	for item in items:
		amount = flt(item.qty) * flt(item.unit_price)
		rows_html += f"""
			<tr>
				<td>{frappe.utils.escape_html(item.description or "")}</td>
				<td style="text-align:center">{flt(item.qty):g}</td>
				<td style="text-align:right">{_fmt_currency(flt(item.unit_price))}</td>
				<td style="text-align:right">{_fmt_currency(amount)}</td>
			</tr>
		"""

	if not items:
		rows_html = """
			<tr>
				<td colspan="4" style="text-align:center; color:#888; padding:24px 0;">
					Nenhum item adicionado
				</td>
			</tr>
		"""

	contract_clause_html = ""
	if doc_type == "contrato":
		contract_clause_html = """
			<div class="clauses">
				<h3>Cláusulas</h3>
				<p><em>[Espaço reservado para o texto jurídico do contrato — objeto,
				prazo, forma de pagamento, rescisão, foro, e demais cláusulas
				aplicáveis. Preencher antes de enviar ao cliente.]</em></p>
			</div>
		"""

	return f"""
	<html>
	<head>
	<meta charset="utf-8">
	<style>
		body {{ font-family: Arial, Helvetica, sans-serif; color: #1a1a1a; padding: 32px; }}
		.header {{ width: 100%; margin-bottom: 32px; }}
		.header td {{ padding: 0; border: none; vertical-align: top; }}
		.brand {{ font-size: 14px; color: #666; text-align: right; }}
		h1 {{ font-size: 24px; margin: 0 0 4px 0; color: {color}; }}
		.meta {{ font-size: 12px; color: #666; margin-bottom: 24px; }}
		table.items {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
		th {{ text-align: left; font-size: 11px; text-transform: uppercase; color: #666; border-bottom: 1px solid #ccc; padding: 8px 4px; }}
		td {{ padding: 10px 4px; border-bottom: 1px solid #eee; font-size: 13px; }}
		table.totals {{ width: 280px; margin-left: auto; margin-top: 16px; font-size: 13px; border-collapse: collapse; }}
		table.totals td {{ border: none; padding: 4px 0; }}
		table.totals td:last-child {{ text-align: right; }}
		table.totals .total td {{ font-weight: bold; font-size: 16px; border-top: 1px solid #ccc; padding-top: 10px; color: {color}; }}
		.clauses {{ margin-top: 40px; }}
	</style>
	</head>
	<body>
		<table class="header">
			<tr>
				<td>
					<h1>{title}</h1>
					<div class="meta">Referência: {frappe.utils.escape_html(deal_name)} &nbsp;•&nbsp; {today}</div>
				</td>
				<td class="brand">{frappe.utils.escape_html(brand_name)}</td>
			</tr>
		</table>
		<div><strong>Cliente:</strong> {frappe.utils.escape_html(client_name)}</div>
		<table class="items">
			<thead>
				<tr>
					<th>Descrição</th>
					<th style="text-align:center">Qtd</th>
					<th style="text-align:right">Preço Unitário</th>
					<th style="text-align:right">Subtotal</th>
				</tr>
			</thead>
			<tbody>
				{rows_html}
			</tbody>
		</table>
		<table class="totals">
			<tr><td>Subtotal</td><td>{_fmt_currency(subtotal)}</td></tr>
			<tr><td>Desconto</td><td>{_fmt_currency(discount)}</td></tr>
			<tr class="total"><td>Total</td><td>{_fmt_currency(total)}</td></tr>
		</table>
		{contract_clause_html}
	</body>
	</html>
	"""
