"""
Seed script for HR-Helpdesk database.
Safe to run multiple times (idempotent update_or_create via Django ORM).
Seeds 20 employees, leave balances, payslips, and HR policies into PostgreSQL/database.
"""

import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_helpdesk.settings')
django.setup()

from helpdesk.management.commands.seed_data import seed_hr_data

if __name__ == "__main__":
    print("Running HR-Helpdesk database seed script...")
    try:
        counts = seed_hr_data()
        print(
            f"[OK] Successfully seeded/updated: {counts['employees']} employees, "
            f"{counts['leave_balances']} leave balances, "
            f"{counts['payslips']} payslips, "
            f"{counts['policies']} HR policies."
        )
    except Exception as e:
        print(f"ERROR during seeding: {e}", file=sys.stderr)
        sys.exit(1)
