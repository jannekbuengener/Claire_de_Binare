#!/bin/sh
set -e
export POSTGRES_PASSWORD="$(cat /run/secrets/postgres_password)"
exec /run.sh "$@"
