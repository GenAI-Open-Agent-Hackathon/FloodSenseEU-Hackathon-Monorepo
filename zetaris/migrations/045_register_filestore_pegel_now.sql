-- FILESTORE table over the CSV ingestion/feeds/pegel_poll.py writes (python tasks.py pegel-poll).
-- Path: /home/zetaris/customer-data/shared/floodsense_live/pegel_now/live.csv, one row per station.
-- New directory, not pegel_levels: the 036 table inferred its schema from the old 7-column header.
-- Run the poller once BEFORE applying this file. inferSchema reads the header at CREATE time and a
-- FILESTORE table cannot be dropped on 2.4.3.1 (see 036). The view is 046.
-- Data: PEGELONLINE, WSV. DL-DE->Zero-2.0. Quelle: WSV, PEGELONLINE.
CREATE LIGHTNING FILESTORE TABLE pegel_now_src FROM floodsense_live_src
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_live/pegel_now", header "true", inferSchema "true")
