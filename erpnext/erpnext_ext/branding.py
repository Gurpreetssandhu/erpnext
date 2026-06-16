"""Per-site branding for this deployment.

Branding is applied PER SITE (not via app-global hooks like ``app_logo_url``),
so each tenant has its own identity: RS Honda and WeFarms are branded
independently. Add a new tenant by adding an entry to ``BRANDS`` and running
``apply_brand`` on that site.

Usage (per site):
    bench --site <site> execute erpnext.erpnext_ext.branding.apply_brand --kwargs '{"brand": "rs_honda"}'
"""

import frappe

BRANDS = {
	"rs_honda": {
		"app_name": "RS Honda",
		"logo": "/assets/erpnext/images/rs_honda.svg",
	},
	"wefarms": {
		"app_name": "WeFarms",
		"logo": "/assets/erpnext/images/wefarms.svg",
	},
}


@frappe.whitelist()
def apply_brand(brand):
	"""Apply a brand from ``BRANDS`` to the current site."""
	cfg = BRANDS.get(brand)
	if not cfg:
		frappe.throw(f"Unknown brand '{brand}'. Known brands: {', '.join(BRANDS)}")

	# Navbar brand logo (Navbar Settings is a per-site single doctype)
	navbar = frappe.get_single("Navbar Settings")
	navbar.app_logo = cfg["logo"]
	navbar.flags.ignore_permissions = True
	navbar.save()

	# App name, favicon, splash, login brand (Website Settings is per-site)
	ws = frappe.get_single("Website Settings")
	ws.app_name = cfg["app_name"]
	ws.app_logo = cfg["logo"]
	ws.favicon = cfg["logo"]
	ws.splash_image = cfg["logo"]
	ws.brand_html = f'<img src="{cfg["logo"]}" alt="{cfg["app_name"]}" style="height:24px">'
	ws.flags.ignore_permissions = True
	ws.save()

	frappe.db.commit()
	frappe.clear_cache()
	return f"Applied brand '{brand}' ({cfg['app_name']}) to site {frappe.local.site}"
