import frappe


def _is_manager(user: str) -> bool:
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	return "System Manager" in roles or "Sales Manager" in roles


def get_task_permission_query_conditions(user=None):
	"""Quem não é gestor só vê as tarefas atribuídas a si ou criadas por si."""
	user = user or frappe.session.user
	if _is_manager(user):
		return ""
	esc = frappe.db.escape(user)
	return f"(`tabCRM Task`.`assigned_to` = {esc} or `tabCRM Task`.`owner` = {esc})"


def has_task_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_manager(user) or ptype == "create" or not doc.get("name"):
		return True
	return user in (doc.get("assigned_to"), doc.get("owner"))