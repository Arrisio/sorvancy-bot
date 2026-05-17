#!/bin/sh
set -e
python scripts/init_db.py
exec python main.py
