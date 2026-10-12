import frappe
from frappe.model.document import Document
from frappe.utils import flt

DIVISAO_CAMPOS = {
	"divisao_prolabore": "divisao_prolabore_pct",
	"divisao_impostos": "divisao_impostos_pct",
	"divisao_crescimento": "divisao_crescimento_pct",
	"divisao_custos": "divisao_custos_pct",
}


class CRMParceria(Document):
	def before_save(self):
		self._calcular_comissao()

	def _calcular_comissao(self):
		"""Quanto a agência ganha nessa parceria específica - comissão % ou valor
		fixo, escolhido parceria a parceria (cada influenciadora/negócio pode ter
		um jeito diferente). Só conta em cima do que já foi pago de verdade (não
		do valor negociado), e só depois de divide pelos mesmos percentuais do
		Financeiro (Configurações → Automações → Divisão do caixa)."""
		pago = flt(self.valor_pago)
		if self.comissao_modelo == "Comissão (%)":
			comissao = pago * flt(self.comissao_pct) / 100 if pago else 0
		elif self.comissao_modelo == "Valor fixo":
			comissao = flt(self.comissao_valor_fixo) if pago else 0
		else:
			comissao = 0
		self.comissao_calculada = comissao

		try:
			from crm.api.automacoes import get_config

			cfg = get_config()
		except Exception:
			cfg = {}
		for campo, chave_pct in DIVISAO_CAMPOS.items():
			self.set(campo, round(comissao * flt(cfg.get(chave_pct)) / 100, 2))
