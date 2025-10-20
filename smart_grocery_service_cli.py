#!/usr/bin/env python3
"""
Thin CLI wrapper delegating to the groceries domain service.

Keeps existing smart_grocery_cli.py intact for formatting helpers and
backward compatibility, while encouraging usage of the service layer.
"""

import argparse
import json

from src.groceries.service import execute as service_execute


def main() -> None:
    parser = argparse.ArgumentParser(description="Groceries Health Basket Analysis (service-based)")
    parser.add_argument("query", help="Natural language query")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM-based intent/analysis")
    args = parser.parse_args()

    result = service_execute(args.query, use_llm=not args.no_llm)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

