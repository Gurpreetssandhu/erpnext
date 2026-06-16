"""Per-site branding for this deployment.

Branding is applied PER SITE (not via app-global hooks like ``app_logo_url``),
so each tenant has its own identity: RS Honda and WeFarms are branded
independently. Add a new tenant by adding an entry to ``BRANDS`` and running
``apply_brand`` on that site.

Logos are tenant data (uploaded as site files under /files/...), so they can be
changed from the UI without rebuilding the image.

Usage (per site):
    bench --site <site> execute erpnext.erpnext_ext.branding.apply_brand --kwargs '{"brand": "rs_honda"}'
"""

import frappe

BRANDS = {
	"rs_honda": {
		"app_name": "RS Honda",
		"logo": "/files/honda-brand.svg",  # Honda mark + "RS Honda" lockup
		"favicon": "/files/honda-logo.png",  # square mark
		"color": "#cc0000",  # Honda red — navbar theme
	},
	"wefarms": {
		"app_name": "WeFarms",
		"logo": "/assets/erpnext/images/wefarms.svg",
		"favicon": "/assets/erpnext/images/wefarms.svg",
		"color": "#2e7d32",  # green
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

	# App name, favicon, splash, brand colour (Website Settings is per-site)
	ws = frappe.get_single("Website Settings")
	ws.app_name = cfg["app_name"]
	ws.app_logo = cfg["logo"]
	ws.favicon = cfg["favicon"]
	ws.splash_image = cfg["favicon"]
	ws.brand_html = f'<img src="{cfg["logo"]}" alt="{cfg["app_name"]}" style="height:24px">'
	if ws.meta.has_field("brand_color"):
		ws.brand_color = cfg["color"]
	ws.flags.ignore_permissions = True
	ws.save()

	frappe.db.commit()
	frappe.clear_cache()
	return f"Applied brand '{brand}' ({cfg['app_name']}, {cfg['color']}) to site {frappe.local.site}"
