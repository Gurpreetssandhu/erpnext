"""Inventory alerting for this deployment.

Detects low-stock and out-of-stock/negative items and dispatches a digest through
a pluggable channel layer. In-app + Email are implemented now; WhatsApp is a stub
to be filled in once the gateway is available — adding it needs no change to the
detection or scheduling code.

Config lives in the single doctype "Inventory Alert Settings". Firings are recorded
in "Inventory Alert Log", which powers the Inventory Alerts dashboard.
"""

import frappe
from frappe.utils import now_datetime


# ---------------------------------------------------------------- detection

def get_low_stock_rows():
	"""Items whose projected qty <= their per-warehouse reorder level."""
	return frappe.db.sql(
		"""
		SELECT b.item_code, b.warehouse, b.actual_qty, b.projected_qty,
			ir.warehouse_reorder_level AS reorder_level
		FROM `tabBin` b
		INNER JOIN `tabItem Reorder` ir
			ON ir.parent = b.item_code AND ir.warehouse = b.warehouse
		INNER JOIN `tabItem` i ON i.name = b.item_code
		WHERE i.disabled = 0 AND i.is_stock_item = 1
			AND ir.warehouse_reorder_level > 0
			AND b.projected_qty <= ir.warehouse_reorder_level
		ORDER BY b.item_code, b.warehouse
		""",
		as_dict=True,
	)


def get_negative_stock_rows():
	"""Items at or below zero actual stock."""
	return frappe.db.sql(
		"""
		SELECT b.item_code, b.warehouse, b.actual_qty, b.projected_qty
		FROM `tabBin` b
		INNER JOIN `tabItem` i ON i.name = b.item_code
		WHERE i.disabled = 0 AND i.is_stock_item = 1 AND b.actual_qty <= 0
		ORDER BY b.actual_qty ASC
		""",
		as_dict=True,
	)


@frappe.whitelist()
def get_low_stock_count():
	"""Number-card value: count of item/warehouse rows below reorder level."""
	return len(get_low_stock_rows())


# ---------------------------------------------------------------- channels

def _send_in_app(users, subject, message):
	for user in users:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": subject,
				"for_user": user,
				"type": "Alert",
				"email_content": message,
			}
		).insert(ignore_permissions=True)


def _send_email(emails, subject, message):
	emails = [e for e in emails if e]
	if not emails:
		return
	# Only attempt if an outgoing email account exists, else it would just error.
	if not frappe.db.exists("Email Account", {"enable_outgoing": 1}):
		frappe.log_error(title="Inventory alerts: no outgoing Email Account configured")
		return
	frappe.sendmail(recipients=emails, subject=subject, message=message, now=False)


def _send_whatsapp(recipients, subject, message):
	# TODO: implement once the WhatsApp gateway is configured.
	# Kept as a no-op so enabling the channel later requires no engine changes.
	pass


def dispatch(subject, message, recipients, channels):
	"""recipients: list of {"user","email"}. channels: list like ["In-App","Email"]."""
	users = [r["user"] for r in recipients if r.get("user")]
	emails = [r["email"] for r in recipients if r.get("email")]
	if "In-App" in channels:
		_send_in_app(users, subject, message)
	if "Email" in channels:
		_send_email(emails, subject, message)
	if "WhatsApp" in channels:
		_send_whatsapp(recipients, subject, message)


# ---------------------------------------------------------------- helpers

def _recipients(settings):
	out = []
	for row in settings.recipients:
		email = row.email or frappe.db.get_value("User", row.user, "email")
		out.append({"user": row.user, "email": email})
	return out


def _digest_html(low, negative):
	html = []
	if low:
		html.append("<h4>Low Stock (below reorder level)</h4>")
		html.append("<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>")
		html.append("<tr><th>Item</th><th>Warehouse</th><th>Projected</th><th>Reorder Level</th></tr>")
		for r in low:
			html.append(
				f"<tr><td>{r.item_code}</td><td>{r.warehouse}</td>"
				f"<td>{r.projected_qty}</td><td>{r.reorder_level}</td></tr>"
			)
		html.append("</table>")
	if negative:
		html.append("<h4>Out of Stock / Negative</h4>")
		html.append("<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>")
		html.append("<tr><th>Item</th><th>Warehouse</th><th>Actual Qty</th></tr>")
		for r in negative:
			html.append(
				f"<tr><td>{r.item_code}</td><td>{r.warehouse}</td><td>{r.actual_qty}</td></tr>"
			)
		html.append("</table>")
	return "".join(html)


def _log(rows, alert_type, channels):
	stamp = now_datetime()
	chan = ", ".join(channels)
	for r in rows:
		frappe.get_doc(
			{
				"doctype": "Inventory Alert Log",
				"alert_type": alert_type,
				"item_code": r.item_code,
				"warehouse": r.warehouse,
				"actual_qty": r.get("actual_qty"),
				"projected_qty": r.get("projected_qty"),
				"reorder_level": r.get("reorder_level"),
				"alert_date": stamp,
				"channels": chan,
			}
		).insert(ignore_permissions=True)


# ---------------------------------------------------------------- entry points

@frappe.whitelist()
def run_inventory_alerts():
	"""Build and dispatch the inventory alert digest. Safe to call manually or on schedule."""
	if not frappe.db.exists("Inventory Alert Settings", "Inventory Alert Settings"):
		return "Inventory Alert Settings not found"
	settings = frappe.get_single("Inventory Alert Settings")
	if not settings.enabled:
		return "Disabled"

	low = get_low_stock_rows() if settings.check_low_stock else []
	negative = get_negative_stock_rows() if settings.check_negative_stock else []
	if not low and not negative:
		return "No inventory alerts"

	channels = []
	if settings.send_in_app:
		channels.append("In-App")
	if settings.send_email:
		channels.append("Email")

	subject = f"Inventory Alerts: {len(low)} low stock, {len(negative)} out of stock"
	message = _digest_html(low, negative)
	recipients = _recipients(settings)

	if channels and recipients:
		dispatch(subject, message, recipients, channels)

	_log(low, "Low Stock", channels)
	_log(negative, "Negative Stock", channels)
	frappe.db.commit()
	return subject


def run_daily():
	"""Scheduler entry (daily). Respects the configured frequency."""
	settings = frappe.get_cached_doc("Inventory Alert Settings") if frappe.db.exists(
		"Inventory Alert Settings", "Inventory Alert Settings"
	) else None
	if settings and settings.enabled and (settings.frequency or "Daily") == "Daily":
		run_inventory_alerts()


def run_hourly():
	if frappe.db.exists("Inventory Alert Settings", "Inventory Alert Settings"):
		settings = frappe.get_cached_doc("Inventory Alert Settings")
		if settings.enabled and settings.frequency == "Hourly":
			run_inventory_alerts()
