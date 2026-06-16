// ERPNext Ext — custom desk behaviour for this deployment.
//
// Make the "Calendar" sidebar workspace open the Event calendar view directly,
// instead of landing on the workspace page. v15 workspaces have no native
// "link" type, so we redirect at the router level.

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
