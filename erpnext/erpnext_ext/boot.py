"""Boot additions for ERPNext Ext.

Exposes the per-site brand colour to the desk so erpnext_ext.bundle.js can paint
the navbar in each tenant's colour (e.g. Honda red for RS Honda).
"""

import frappe


def boot_session(bootinfo):
	try:
		bootinfo.brand_color = frappe.db.get_single_value("Website Settings", "brand_color")
	except Exception:
		bootinfo.brand_color = None
