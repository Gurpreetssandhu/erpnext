"""Idempotent setup for ERPNext Ext, run on ``after_migrate``.

Makes two pieces of configuration permanent and reproducible on any site
(RS Honda, WeFarms, and future tenants):

1. Sidebar module hiding — restrict each module workspace to its roles so users
   only see modules they have access to (the built-in ``is_permitted`` engine).
2. The Calendar sidebar item — a "Calendar User" role that gates a Calendar
   workspace and grants full Event permissions.

Branding is intentionally NOT here — it is per-site (see ``branding.py``).
"""

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.permissions import add_permission, update_permission_property

SYSTEM_MANAGER = "System Manager"

# Each module workspace -> the roles that should see it. System Manager is added
# to all so admins keep full visibility; Administrator always sees everything.
WORKSPACE_ROLES = {
	"Accounting": ["Accounts User", "Accounts Manager", "Auditor"],
	"Payables": ["Accounts User", "Accounts Manager"],
	"Receivables": ["Accounts User", "Accounts Manager"],
	"Financial Reports": ["Accounts User", "Accounts Manager", "Auditor"],
	"Assets": ["Accounts User", "Accounts Manager", "Stock Manager"],
	"Buying": ["Purchase User", "Purchase Manager", "Stock Manager"],
	"Selling": ["Sales User", "Sales Manager"],
	"CRM": ["Sales User", "Sales Manager"],
	"Stock": ["Stock User", "Stock Manager", "Item Manager"],
	"Manufacturing": ["Manufacturing User", "Manufacturing Manager"],
	"Quality": ["Quality Manager"],
	"Projects": ["Projects User", "Projects Manager"],
	"Support": ["Support Team"],
	"Website": ["Website Manager", "Blogger"],
	"Users": [SYSTEM_MANAGER],
	"Build": [SYSTEM_MANAGER],
	"ERPNext Settings": [SYSTEM_MANAGER],
	"Integrations": [SYSTEM_MANAGER],
	"ERPNext Integrations": [SYSTEM_MANAGER],
}


def apply_workspace_role_hiding():
	for ws_name, roles in WORKSPACE_ROLES.items():
		if not frappe.db.exists("Workspace", ws_name):
			continue
		wanted = [r for r in dict.fromkeys([*roles, SYSTEM_MANAGER]) if frappe.db.exists("Role", r)]
		doc = frappe.get_doc("Workspace", ws_name)
		if sorted(r.role for r in doc.roles) == sorted(wanted):
			continue
		doc.set("roles", [{"role": r} for r in wanted])
		doc.flags.ignore_permissions = True
		doc.save()


def setup_calendar():
	# Role that gates the Calendar sidebar item (toggle it via a Role Profile)
	if not frappe.db.exists("Role", "Calendar User"):
		frappe.get_doc(
			{"doctype": "Role", "role_name": "Calendar User", "desk_access": 1}
		).insert(ignore_permissions=True)

	# Full Event actions (create/edit/delete) for Calendar Users
	if not frappe.db.exists("Custom DocPerm", {"parent": "Event", "role": "Calendar User"}):
		add_permission("Event", "Calendar User", 0)
	for ptype in ("read", "write", "create", "delete"):
		update_permission_property("Event", "Calendar User", 0, ptype, 1)

	# Calendar workspace (sidebar item); the erpnext_ext.bundle.js redirect opens
	# the actual calendar view on click. Shortcut kept as a fallback.
	content = json.dumps(
		[
			{"id": "calh", "type": "header", "data": {"text": '<span class="h4"><b>Calendar</b></span>', "col": 12}},
			{"id": "cals", "type": "shortcut", "data": {"shortcut_name": "My Calendar", "col": 4}},
		]
	)
	if frappe.db.exists("Workspace", "Calendar"):
		ws = frappe.get_doc("Workspace", "Calendar")
	else:
		ws = frappe.new_doc("Workspace")
		ws.title = "Calendar"
		ws.label = "Calendar"
	ws.public = 1
	ws.icon = "calendar"
	ws.sequence_id = 99
	ws.content = content
	ws.set("shortcuts", [{"type": "URL", "label": "My Calendar", "url": "/app/event/view/calendar/default", "color": "Blue"}])
	ws.set("roles", [{"role": "Calendar User"}, {"role": SYSTEM_MANAGER}])
	ws.flags.ignore_permissions = True
	ws.save()


def ensure_custom_fields():
	# Per-site navbar theme colour, editable from the UI (Website Settings → Brand Color)
	create_custom_fields(
		{
			"Website Settings": [
				{
					"fieldname": "brand_color",
					"label": "Brand Color",
					"fieldtype": "Color",
					"insert_after": "app_name",
					"description": "Navbar theme colour for this site (ERPNext Ext)",
				}
			]
		},
		ignore_validate=True,
	)


def _ensure_number_card(label, props):
	existing = frappe.db.get_value("Number Card", {"label": label})
	if existing:
		return existing
	doc = frappe.get_doc({"doctype": "Number Card", "label": label, "is_public": 1, "module": "ERPNext Ext", **props})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def setup_inventory_alerts():
	"""Inventory Alerts dashboard: number cards + workspace (idempotent)."""
	low = _ensure_number_card(
		"Low Stock Items",
		{"type": "Custom", "method": "erpnext.erpnext_ext.inventory_alerts.get_low_stock_count"},
	)
	neg = _ensure_number_card(
		"Out of Stock / Negative",
		{"type": "Document Type", "document_type": "Bin", "function": "Count", "filters_json": json.dumps([["Bin", "actual_qty", "<=", 0]])},
	)
	logged = _ensure_number_card(
		"Inventory Alerts Logged",
		{"type": "Document Type", "document_type": "Inventory Alert Log", "function": "Count", "filters_json": json.dumps([])},
	)

	content = json.dumps(
		[
			{"id": "iah", "type": "header", "data": {"text": '<span class="h4"><b>Inventory Alerts</b></span>', "col": 12}},
			{"id": "ianc1", "type": "number_card", "data": {"number_card_name": low, "col": 4}},
			{"id": "ianc2", "type": "number_card", "data": {"number_card_name": neg, "col": 4}},
			{"id": "ianc3", "type": "number_card", "data": {"number_card_name": logged, "col": 4}},
			{"id": "iasc1", "type": "shortcut", "data": {"shortcut_name": "Low Stock Items", "col": 4}},
			{"id": "iasc2", "type": "shortcut", "data": {"shortcut_name": "Alert Log", "col": 4}},
			{"id": "iasc3", "type": "shortcut", "data": {"shortcut_name": "Alert Settings", "col": 4}},
		]
	)
	if frappe.db.exists("Workspace", "Inventory Alerts"):
		ws = frappe.get_doc("Workspace", "Inventory Alerts")
	else:
		ws = frappe.new_doc("Workspace")
		ws.title = "Inventory Alerts"
		ws.label = "Inventory Alerts"
	ws.public = 1
	ws.icon = "alert"
	ws.sequence_id = 98
	ws.content = content
	ws.set(
		"shortcuts",
		[
			{"type": "Report", "label": "Low Stock Items", "link_to": "Low Stock Items", "color": "Yellow"},
			{"type": "DocType", "label": "Alert Log", "link_to": "Inventory Alert Log", "color": "Grey"},
			{"type": "DocType", "label": "Alert Settings", "link_to": "Inventory Alert Settings", "color": "Blue"},
		],
	)
	ws.set(
		"number_cards",
		[
			{"number_card_name": low, "label": "Low Stock Items"},
			{"number_card_name": neg, "label": "Out of Stock / Negative"},
			{"number_card_name": logged, "label": "Inventory Alerts Logged"},
		],
	)
	ws.set("roles", [{"role": "Stock User"}, {"role": "Stock Manager"}, {"role": "Purchase Manager"}, {"role": "System Manager"}])
	ws.flags.ignore_permissions = True
	ws.save()


def after_migrate():
	"""Entry point wired in hooks.py. Kept resilient so a failure never breaks migrate."""
	try:
		ensure_custom_fields()
		setup_calendar()
		apply_workspace_role_hiding()
		setup_inventory_alerts()
		frappe.db.commit()
	except Exception:
		frappe.log_error(title="erpnext_ext after_migrate failed")
