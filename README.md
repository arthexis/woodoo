Magical Odoo Addons
===================

This repository contains the source code for various Odoo addons.

Datacenter
---------------------------

Tools for enterprise datacenter administration.

- Models for:
  - Server
  - Application
  - Database

WooCommerce Satellite
---------------------------

Each WooCommerce store is a satellite. This module allows you to connect multiple WooCommerce stores to a single Odoo instance.

- When products are sold on WooCommerce, a Sales Order is created in Odoo.
- When products are sold or updated in Odoo, the stock is updated in WooCommerce.

Changes in WooCommerce do not affect Odoo and will be overwritten during synchronization, Odoo is the source of truth for the stock.

OCPP Charging Station
--------------------------------

This module is used to integrate Odoo with an OCPP compliant charging station. It allows you to manage charging stations, connectors, charging sessions and charging cards.

Site Inspection
---------------------------

Store on-site inspection data to generate reports and estimates.

This module allows you to define inspection templates and generate reports and estimates from them.

Included inspection variants:

- General Inspection
- Electrical Inspection

Game Profile
---------------------------

Store game profile data to generate reports and estimates.

Profiles can be linked to a user and a game, as well as provide a list of achievements.

Products and services can be linked to a profile to generate estimates.

Games can use the Odoo API to retrieve profile data.
