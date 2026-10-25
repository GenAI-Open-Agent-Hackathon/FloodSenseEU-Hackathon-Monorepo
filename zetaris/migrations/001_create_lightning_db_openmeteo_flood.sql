-- Lightning database for the Open-Meteo Flood (GloFAS) REST table.
-- No IF NOT EXISTS in Lightning SQL (tested 2026-10-24, Zetaris 2.4.3.1).
-- Re-running answers "already exists" and the sync tool skips it.
-- The description allows only letters, digits, space, _ . - and , (no parentheses).
CREATE LIGHTNING DATABASE OPENMETEO_FLOOD DESCRIBE BY "Open-Meteo Flood API - GloFAS - Valencia points"
