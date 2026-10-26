#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    python src/manage.py migrate --noinput
fi

if [ "${SEED_DEMO_DATA:-true}" = "true" ]; then
    python src/manage.py seed_assessment_data
fi

exec "$@"
