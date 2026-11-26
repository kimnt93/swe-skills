#!/usr/bin/env python3
"""The fixture shop's command line, with the same faults as the web app: total works, coupon crashes, report is slow."""

import sys
import time

command, *rest = sys.argv[1:] or [""]
if command == "total":
    print(f"Total: {int(rest[0]) * 999 / 100:.2f}")
elif command == "coupon":
    raise RuntimeError(f"coupon {rest[0]}: price table is missing")
elif command == "report":
    time.sleep(1.5)
    print("Report ready: 12 orders")
else:
    sys.exit("usage: shop_cli.py total <quantity> | coupon <code> | report")
