"""
Django management command to seed HR-Helpdesk database using Django ORM.
Idempotent and safe to run multiple times (uses update_or_create).
Seeds 20 employees, leave balances, multi-month payslips, and HR policies.
"""

from decimal import Decimal
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from helpdesk.models import Employee, LeaveBalance, Payslip, HRPolicy

EMPLOYEES = [
    {"employee_id": "EMP001", "name": "Alice Johnson", "email": "alice.johnson@example.com", "department": "Engineering", "designation": "Staff Software Engineer", "joining_date": "2021-04-12", "manager": "EMP005", "status": "Active"},
    {"employee_id": "EMP002", "name": "Bob Smith", "email": "bob.smith@example.com", "department": "Engineering", "designation": "Frontend Developer", "joining_date": "2022-08-01", "manager": "EMP001", "status": "Active"},
    {"employee_id": "EMP003", "name": "Carol Williams", "email": "carol.williams@example.com", "department": "Human Resources", "designation": "HR Generalist", "joining_date": "2020-01-15", "manager": "EMP008", "status": "Active"},
    {"employee_id": "EMP004", "name": "David Brown", "email": "david.brown@example.com", "department": "Marketing", "designation": "Content Marketing Lead", "joining_date": "2022-11-20", "manager": "EMP010", "status": "Active"},
    {"employee_id": "EMP005", "name": "Elena Rostova", "email": "elena.rostova@example.com", "department": "Engineering", "designation": "VP of Engineering", "joining_date": "2019-06-01", "manager": "CEO", "status": "Active"},
    {"employee_id": "EMP006", "name": "Frank Miller", "email": "frank.miller@example.com", "department": "Finance", "designation": "Senior Financial Analyst", "joining_date": "2021-09-10", "manager": "EMP014", "status": "Active"},
    {"employee_id": "EMP007", "name": "Grace Hopper", "email": "grace.hopper@example.com", "department": "Engineering", "designation": "DevOps Architect", "joining_date": "2020-03-01", "manager": "EMP005", "status": "Active"},
    {"employee_id": "EMP008", "name": "Henry Adams", "email": "henry.adams@example.com", "department": "Human Resources", "designation": "Head of People Operations", "joining_date": "2018-05-14", "manager": "CEO", "status": "Active"},
    {"employee_id": "EMP009", "name": "Irene Adler", "email": "irene.adler@example.com", "department": "Product", "designation": "Senior Product Manager", "joining_date": "2021-02-18", "manager": "EMP012", "status": "Active"},
    {"employee_id": "EMP010", "name": "Jack Davies", "email": "jack.davies@example.com", "department": "Marketing", "designation": "Chief Marketing Officer", "joining_date": "2019-01-10", "manager": "CEO", "status": "Active"},
    {"employee_id": "EMP011", "name": "Kavita Rao", "email": "kavita.rao@example.com", "department": "Engineering", "designation": "QA Automation Lead", "joining_date": "2022-04-05", "manager": "EMP005", "status": "Active"},
    {"employee_id": "EMP012", "name": "Liam Murphy", "email": "liam.murphy@example.com", "department": "Product", "designation": "VP of Product", "joining_date": "2019-10-15", "manager": "CEO", "status": "Active"},
    {"employee_id": "EMP013", "name": "Maya Lin", "email": "maya.lin@example.com", "department": "Design", "designation": "Lead UI/UX Designer", "joining_date": "2021-07-22", "manager": "EMP012", "status": "Active"},
    {"employee_id": "EMP014", "name": "Noah Campbell", "email": "noah.campbell@example.com", "department": "Finance", "designation": "Chief Financial Officer", "joining_date": "2018-03-01", "manager": "CEO", "status": "Active"},
    {"employee_id": "EMP015", "name": "Olivia Taylor", "email": "olivia.taylor@example.com", "department": "Sales", "designation": "Account Executive", "joining_date": "2023-01-09", "manager": "EMP017", "status": "Active"},
    {"employee_id": "EMP016", "name": "Patrick Stewart", "email": "patrick.stewart@example.com", "department": "Sales", "designation": "Business Development Rep", "joining_date": "2023-06-15", "manager": "EMP017", "status": "Active"},
    {"employee_id": "EMP017", "name": "Rachel Green", "email": "rachel.green@example.com", "department": "Sales", "designation": "VP of Sales", "joining_date": "2019-08-20", "manager": "CEO", "status": "Active"},
    {"employee_id": "EMP018", "name": "Siddharth Verma", "email": "siddharth.verma@example.com", "department": "Engineering", "designation": "Backend Engineer", "joining_date": "2023-03-01", "manager": "EMP001", "status": "Active"},
    {"employee_id": "EMP019", "name": "Tara O'Connor", "email": "tara.oconnor@example.com", "department": "Legal", "designation": "Corporate Counsel", "joining_date": "2020-12-01", "manager": "CEO", "status": "Active"},
    {"employee_id": "EMP020", "name": "Uma Thurman", "email": "uma.thurman@example.com", "department": "Customer Support", "designation": "Support Team Lead", "joining_date": "2022-02-14", "manager": "EMP008", "status": "Active"},
]

LEAVE_BALANCES = [
    {"employee_id": "EMP001", "year": 2026, "annual_leave": 16.5, "sick_leave": 9.0, "casual_leave": 4.0, "parental_leave": 60.0, "comp_off": 2.0},
    {"employee_id": "EMP002", "year": 2026, "annual_leave": 12.0, "sick_leave": 7.5, "casual_leave": 3.0, "parental_leave": 60.0, "comp_off": 1.0},
    {"employee_id": "EMP003", "year": 2026, "annual_leave": 18.0, "sick_leave": 10.0, "casual_leave": 5.0, "parental_leave": 60.0, "comp_off": 0.0},
    {"employee_id": "EMP004", "year": 2026, "annual_leave": 14.0, "sick_leave": 8.0, "casual_leave": 2.5, "parental_leave": 60.0, "comp_off": 3.0},
    {"employee_id": "EMP005", "year": 2026, "annual_leave": 22.0, "sick_leave": 10.0, "casual_leave": 5.0, "parental_leave": 60.0, "comp_off": 4.0},
    {"employee_id": "EMP006", "year": 2026, "annual_leave": 15.0, "sick_leave": 9.0, "casual_leave": 4.0, "parental_leave": 60.0, "comp_off": 0.0},
    {"employee_id": "EMP007", "year": 2026, "annual_leave": 19.5, "sick_leave": 10.0, "casual_leave": 5.0, "parental_leave": 60.0, "comp_off": 2.0},
    {"employee_id": "EMP008", "year": 2026, "annual_leave": 21.0, "sick_leave": 10.0, "casual_leave": 5.0, "parental_leave": 60.0, "comp_off": 0.0},
    {"employee_id": "EMP009", "year": 2026, "annual_leave": 17.0, "sick_leave": 8.5, "casual_leave": 3.0, "parental_leave": 60.0, "comp_off": 1.0},
    {"employee_id": "EMP010", "year": 2026, "annual_leave": 20.0, "sick_leave": 10.0, "casual_leave": 5.0, "parental_leave": 60.0, "comp_off": 0.0},
    {"employee_id": "EMP011", "year": 2026, "annual_leave": 13.5, "sick_leave": 6.0, "casual_leave": 2.0, "parental_leave": 60.0, "comp_off": 2.0},
    {"employee_id": "EMP012", "year": 2026, "annual_leave": 20.0, "sick_leave": 10.0, "casual_leave": 4.0, "parental_leave": 60.0, "comp_off": 1.0},
    {"employee_id": "EMP013", "year": 2026, "annual_leave": 15.0, "sick_leave": 9.0, "casual_leave": 3.5, "parental_leave": 60.0, "comp_off": 0.0},
    {"employee_id": "EMP014", "year": 2026, "annual_leave": 24.0, "sick_leave": 10.0, "casual_leave": 5.0, "parental_leave": 60.0, "comp_off": 0.0},
    {"employee_id": "EMP015", "year": 2026, "annual_leave": 11.0, "sick_leave": 5.0, "casual_leave": 2.0, "parental_leave": 60.0, "comp_off": 3.0},
    {"employee_id": "EMP016", "year": 2026, "annual_leave": 10.0, "sick_leave": 8.0, "casual_leave": 1.5, "parental_leave": 60.0, "comp_off": 0.0},
    {"employee_id": "EMP017", "year": 2026, "annual_leave": 22.0, "sick_leave": 10.0, "casual_leave": 5.0, "parental_leave": 60.0, "comp_off": 1.0},
    {"employee_id": "EMP018", "year": 2026, "annual_leave": 14.0, "sick_leave": 7.0, "casual_leave": 3.0, "parental_leave": 60.0, "comp_off": 1.0},
    {"employee_id": "EMP019", "year": 2026, "annual_leave": 18.0, "sick_leave": 9.5, "casual_leave": 4.0, "parental_leave": 60.0, "comp_off": 0.0},
    {"employee_id": "EMP020", "year": 2026, "annual_leave": 16.0, "sick_leave": 8.0, "casual_leave": 3.0, "parental_leave": 60.0, "comp_off": 2.0},
]

BASE_SALARIES = {
    "EMP001": 8500, "EMP002": 5200, "EMP003": 5800, "EMP004": 6200, "EMP005": 14000,
    "EMP006": 6800, "EMP007": 9200, "EMP008": 11000, "EMP009": 8900, "EMP010": 13500,
    "EMP011": 7100, "EMP012": 12500, "EMP013": 7400, "EMP014": 15000, "EMP015": 5600,
    "EMP016": 4800, "EMP017": 13000, "EMP018": 5400, "EMP019": 9800, "EMP020": 6000,
}

POLICIES = [
    {
        "policy_id": "POL_ANNUAL_LEAVE",
        "title": "Annual Leave & Vacation Policy",
        "category": "Leave & Attendance",
        "content": (
            "1. Entitlement: Full-time employees receive 20 paid annual leave days per calendar year, accrued monthly (1.67 days/month).\n"
            "2. Rollover: A maximum of 5 unused annual leave days can be carried over into the following calendar year, expiring on March 31st.\n"
            "3. Notice Requirement: Leave requests of 1-3 days require 48 hours notice. Leave requests of 4 or more consecutive days require at least 2 weeks advance notice.\n"
            "4. Approval: All annual leave requests must be approved by the reporting manager via HR-Helpdesk."
        )
    },
    {
        "policy_id": "POL_SICK_LEAVE",
        "title": "Sick & Medical Leave Policy",
        "category": "Leave & Attendance",
        "content": (
            "1. Entitlement: Employees receive 10 paid sick leave days per year, available from day one.\n"
            "2. Notification: In case of unexpected illness, employees must notify their manager and log the leave by 9:00 AM on the day of absence.\n"
            "3. Medical Certificate: An authorized physician's certificate is mandatory for consecutive sick leave exceeding 2 working days.\n"
            "4. Rollover: Sick leave does not carry over to the next year and cannot be encashed upon separation."
        )
    },
    {
        "policy_id": "POL_PARENTAL_LEAVE",
        "title": "Parental & Maternity / Paternity Policy",
        "category": "Leave & Attendance",
        "content": (
            "1. Primary Caregiver (Maternity): 16 consecutive weeks of 100% paid leave for childbirth or adoption of a child under age 5.\n"
            "2. Secondary Caregiver (Paternity): 4 consecutive weeks of 100% paid leave to be taken within the first 6 months following birth or adoption.\n"
            "3. Eligibility: Available to all full-time employees with at least 6 months of continuous service.\n"
            "4. Notification: Primary caregiver must give written notice at least 8 weeks prior to the anticipated start date."
        )
    },
    {
        "policy_id": "POL_REMOTE_WORK",
        "title": "Remote Work & Hybrid Workplace Policy",
        "category": "Workplace Guidelines",
        "content": (
            "1. Hybrid Schedule: Eligible employees may work remotely up to 3 days per week with team manager coordination.\n"
            "2. Core Hours: All remote team members must be reachable and responsive during core team hours: 10:00 AM to 4:00 PM local time.\n"
            "3. Internet Subsidy: A monthly tax-free stipend of $50 is added to monthly payroll for high-speed home internet maintenance.\n"
            "4. Security: Remote work must strictly comply with company IT security protocols (VPN usage, screen lock, zero sensitive data on personal devices)."
        )
    },
    {
        "policy_id": "POL_EXPENSE_REIMBURSEMENT",
        "title": "Travel & Expense Reimbursement Policy",
        "category": "Finance & Benefits",
        "content": (
            "1. Filing Deadline: All business expenses must be submitted within 30 calendar days of expense occurrence with itemized receipts.\n"
            "2. Per Diem / Meals: Daily meal cap for business travel is $75 per day (breakfast $15, lunch $25, dinner $35). Alcoholic beverages are excluded.\n"
            "3. Flights & Lodging: Flights under 6 hours must be booked in economy class. Lodging cap is $220/night in standard cities, $320/night in high-cost metro areas.\n"
            "4. Processing: Approved reimbursements are paid with the subsequent monthly payroll cycle."
        )
    },
    {
        "policy_id": "POL_CODE_OF_CONDUCT",
        "title": "Code of Conduct & Workplace Harassment Policy",
        "category": "Workplace Ethics",
        "content": (
            "1. Zero Tolerance: The company strictly prohibits harassment, discrimination, or retaliation based on gender, race, religion, sexual orientation, disability, or age.\n"
            "2. Confidential Reporting: Concerns can be reported directly to People Operations, or confidentially via ethics@company.com or the toll-free hotline.\n"
            "3. Investigation: All claims are investigated within 5 business days by an independent panel with strict non-retaliation guarantees."
        )
    },
    {
        "policy_id": "POL_HEALTH_INSURANCE",
        "title": "Health Insurance & Wellness Benefits Policy",
        "category": "Finance & Benefits",
        "content": (
            "1. Medical Coverage: 100% company-paid premium for the employee, and 80% coverage for eligible dependents (spouse and children under 26).\n"
            "2. Annual Wellness: Up to $300 reimbursement per year for preventive health screenings and routine dental/vision checkups.\n"
            "3. Gym & Fitness: $40 monthly fitness reimbursement for certified gym memberships, yoga studios, or fitness apps."
        )
    },
    {
        "policy_id": "POL_PROBATION_NOTICE",
        "title": "Probation Period & Resignation Notice Policy",
        "category": "Employment Terms",
        "content": (
            "1. Probationary Period: New hires undergo a 3-month probation period evaluated by their department manager.\n"
            "2. Notice During Probation: Either party may terminate employment with 2 weeks written notice during probation.\n"
            "3. Notice Post-Confirmation: Confirmed employees must provide 60 calendar days (or manager-approved buyout) written notice before departure."
        )
    }
]


def seed_hr_data():
    """
    Executes idempotent seeding of Employee, LeaveBalance, Payslip, and HRPolicy.
    Returns counts dict.
    """
    counts = {"employees": 0, "leave_balances": 0, "payslips": 0, "policies": 0}

    with transaction.atomic():
        # 1. Employees
        emp_map = {}
        for emp_data in EMPLOYEES:
            obj, _ = Employee.objects.update_or_create(
                employee_id=emp_data["employee_id"],
                defaults={
                    "name": emp_data["name"],
                    "email": emp_data["email"],
                    "department": emp_data["department"],
                    "designation": emp_data["designation"],
                    "joining_date": datetime.strptime(emp_data["joining_date"], "%Y-%m-%d").date(),
                    "manager": emp_data["manager"],
                    "status": emp_data["status"]
                }
            )
            emp_map[emp_data["employee_id"]] = obj
            counts["employees"] += 1

        # 2. Leave Balances
        for lb in LEAVE_BALANCES:
            emp = emp_map.get(lb["employee_id"])
            if emp:
                LeaveBalance.objects.update_or_create(
                    employee=emp,
                    year=lb["year"],
                    defaults={
                        "annual_leave": Decimal(str(lb["annual_leave"])),
                        "sick_leave": Decimal(str(lb["sick_leave"])),
                        "casual_leave": Decimal(str(lb["casual_leave"])),
                        "parental_leave": Decimal(str(lb["parental_leave"])),
                        "comp_off": Decimal(str(lb["comp_off"]))
                    }
                )
                counts["leave_balances"] += 1

        # 3. Payslips (August 2026 and September 2026)
        months = [("August", 2026, "2026-08-31"), ("September", 2026, "2026-09-30")]
        for emp_data in EMPLOYEES:
            emp = emp_map.get(emp_data["employee_id"])
            base = BASE_SALARIES.get(emp_data["employee_id"], 6000)
            hra = round(base * 0.30, 2)
            allowance = round(base * 0.15, 2)
            gross = round(base + hra + allowance, 2)

            tax = round(gross * 0.18, 2)
            pf = round(base * 0.06, 2)
            health_insurance = 120.00
            total_deductions = round(tax + pf + health_insurance, 2)
            net_pay = round(gross - total_deductions, 2)

            for month_name, year_num, disb_date in months:
                Payslip.objects.update_or_create(
                    employee=emp,
                    month=month_name,
                    year=year_num,
                    defaults={
                        "basic_salary": Decimal(str(base)),
                        "hra": Decimal(str(hra)),
                        "allowances": Decimal(str(allowance)),
                        "gross_salary": Decimal(str(gross)),
                        "tax_deduction": Decimal(str(tax)),
                        "pf_deduction": Decimal(str(pf)),
                        "insurance_deduction": Decimal(str(health_insurance)),
                        "total_deductions": Decimal(str(total_deductions)),
                        "net_salary": Decimal(str(net_pay)),
                        "currency": "USD",
                        "payment_status": "Paid",
                        "disbursement_date": datetime.strptime(disb_date, "%Y-%m-%d").date()
                    }
                )
                counts["payslips"] += 1

        # 4. HR Policies
        for pol in POLICIES:
            HRPolicy.objects.update_or_create(
                policy_id=pol["policy_id"],
                defaults={
                    "title": pol["title"],
                    "category": pol["category"],
                    "content": pol["content"]
                }
            )
            counts["policies"] += 1

    return counts


class Command(BaseCommand):
    help = "Idempotently seeds PostgreSQL database with fake employee records, leave balances, payslips, and HR policies."

    def handle(self, *args, **options):
        self.stdout.write("Seeding database via Django ORM...")
        try:
            counts = seed_hr_data()
            self.stdout.write(self.style.SUCCESS(
                f"[OK] Successfully seeded/updated: {counts['employees']} employees, "
                f"{counts['leave_balances']} leave balances, "
                f"{counts['payslips']} payslips, "
                f"{counts['policies']} HR policies."
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during seeding: {str(e)}"))
            raise
