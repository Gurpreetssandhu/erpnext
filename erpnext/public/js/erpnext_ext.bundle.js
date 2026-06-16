// ERPNext Ext — custom desk behaviour for this deployment.

// 1) Calendar: make the "Calendar" sidebar workspace open the Event calendar
//    view directly, instead of landing on the workspace page. v15 workspaces
//    have no native "link" type, so we redirect at the router level.
frappe.router.on("change", () => {
	const route = frappe.get_route() || [];
	const first = (route[0] || "").toLowerCase();
	const second = (route[1] || "").toLowerCase();
	const is_calendar_workspace =
		first === "calendar" || (first === "workspaces" && second === "calendar");
	if (is_calendar_workspace) {
		// route[0] === "event" on the real calendar view, so this never loops
		frappe.set_route("event", "view", "calendar", "default");
	}
});

// 2) Branding: paint the navbar in the per-tenant brand colour (boot.brand_color),
//    e.g. Honda red for RS Honda. Set per site in Website Settings → Brand Color.
function apply_brand_navbar() {
	const color = frappe.boot && frappe.boot.brand_color;
	if (!color) return;

	document.documentElement.style.setProperty("--navbar-bg", color);

	if (!document.getElementById("erpnext-ext-navbar-style")) {
		const style = document.createElement("style");
		style.id = "erpnext-ext-navbar-style";
		style.textContent = `
			.navbar.navbar-expand {
				background-color: ${color} !important;
				border-bottom: 1px solid ${color} !important;
			}
			.navbar.navbar-expand .navbar-brand,
			.navbar.navbar-expand .nav-link,
			.navbar.navbar-expand a.text-muted,
			.navbar.navbar-expand .navbar-text { color: #fff !important; }
			.navbar.navbar-expand .navbar-icon svg,
			.navbar.navbar-expand .icon { stroke: #fff !important; }
		`;
		document.head.appendChild(style);
	}
}
$(document).on("startup", apply_brand_navbar);
$(apply_brand_navbar);
