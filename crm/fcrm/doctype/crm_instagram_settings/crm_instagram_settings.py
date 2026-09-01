# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt

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
		verify_token: DF.Data | None
	# end: auto-generated types

	pass
