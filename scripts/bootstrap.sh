#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install kaggle

echo "セットアップ完了。"
echo "次: PYTHONPATH=src python -m kaggle_comp_monitor.main --config config/config.example.yml"
