Odoo Addons for WooCommerce Integrations
========================================

This repository contains the source code for the various Odoo addons that are used to integrate Odoo with WooCommerce.

1. WooCommerce Site integrator.
2. OCPP Charging Station integrator.

WooCommerce Satellite
---------------------------

Each WooCommerce store is a satellite. This module allows you to connect multiple WooCommerce stores to a single Odoo instance.

* When products are sold on WooCommerce, a Sales Order is created in Odoo.
* When products are sold or updated in Odoo, the stock is updated in WooCommerce.

Changes in WooCommerce do not affect Odoo and will be overwritten during synchronization, Odoo is the source of truth for the stock.

OCPP Charging Station
--------------------------------

This module is used to integrate Odoo with an OCPP compliant charging station. It allows you to manage charging stations, connectors, charging sessions and charging cards.
