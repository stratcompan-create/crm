# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CRMInstagramSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		access_token: DF.Password | None
		app_secret: DF.Password | None
		enabled: DF.Check
		instagram_business_account_id: DF.Data | None
		token_expires_on: DF.Date | None
		verify_token: DF.Data | None
	# end: auto-generated types

	def validate(self):
		if not self.has_value_changed("access_token") or not self.access_token:
			return
		from crm.api.instagram import fetch_profile

		profile = fetch_profile(self.get_password("access_token"))
		if not profile:
			frappe.msgprint(
				_(
					"Não foi possível confirmar este token com o Instagram. Salvo mesmo assim, mas confira se ele está correto."
				),
				alert=True,
				indicator="orange",
			)
			return
		self.instagram_business_account_id = profile.get("id") or self.instagram_business_account_id
		# duram ~60 dias; a primeira renovação automática só é tentada perto do vencimento
		self.token_expires_on = frappe.utils.add_days(frappe.utils.nowdate(), 58)
		frappe.msgprint(
			_("Conectado à conta @{0} do Instagram.").format(profile.get("username")),
			alert=True,
			indicator="green",
		)
