#!/bin/bash
# Agent1 Omni quick launcher
cd "$(dirname "$0")"
[ -f .env ] || cp .env.example .env
python3 -m agent1.cli "$@"
