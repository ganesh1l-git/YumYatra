#!/bin/bash
# Vercel Build Script for YumYatra Django
echo "==> Installing Python dependencies..."
python3 -m pip install -r requirements.txt

echo "==> Collecting static assets..."
python3 YumYatra/manage.py collectstatic --noinput --clear

echo "==> Running database migrations..."
python3 YumYatra/manage.py migrate --noinput

echo "==> Seeding initial restaurant & menu data..."
python3 YumYatra/manage.py seed_db || true

echo "==> Vercel Build Completed Successfully!"
