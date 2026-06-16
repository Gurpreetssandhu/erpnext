# ERPNext Ext

In-fork customization module for this deployment (branch `erpnext_ext-develop`).

## What lives here

- **Branding** — assets in `erpnext/public/images/`; theme partial `_erpnext_ext_theme.scss`;
  small overrides in `erpnext/hooks.py` (`app_logo_url`, `website_context`, `email_brand_image`,
  `add_to_apps_screen`).
- **Alerts** — a thin layer over Frappe's native `Notification` engine:
  - `alerts/inventory_low_stock.py` — scheduled low-stock check (reuses
    `erpnext/stock/reorder_item.py` helpers), notification-only and configurable-frequency.
  - native `Notification` records for expiry / negative stock, shipped as fixtures.
  - `Alerts Center` workspace (console + dashboard).
- **Configs** — other ERPNext customizations and fixtures.

## Principle

Keep our code in new files inside this module. Edits to existing core files are minimal,
localized, and commented so `git pull upstream develop` stays easy to reconcile.
Generic, non-branding pieces are kept separable so they can be contributed upstream later.
