"""
HR-Helpdesk Tools.
Implements the 6 required tools for:
  - HR Reads: leave balance, payslips, company policy (via Supabase PostgreSQL models)
  - Compute: leave days calculator (Python business day math)
  - Write: submit leave request (persists to Supabase PostgreSQL)
  - Live: current system date and time
"""

import uuid
from datetime import datetime, timedelta
from django.db.models import Q
from helpdesk.models import Employee, LeaveBalance, Payslip, HRPolicy, LeaveRequest


def _resolve_employee(employee_id_or_name: str) -> Employee | None:
    """Helper to find an Employee instance whether employee_id or name was provided."""
    clean_query = employee_id_or_name.strip()
    emp = Employee.objects.filter(employee_id__iexact=clean_query).first()
    if emp:
        return emp
    return Employee.objects.filter(name__icontains=clean_query).first()


def get_leave_balance(employee_id: str, year: int = 2026) -> dict:
    """
    Fetch employee leave balance records from PostgreSQL.
    Args:
        employee_id: Unique employee ID (e.g. 'EMP001') or employee name.
        year: Calendar year (defaults to 2026).
    """
    try:
        emp = _resolve_employee(employee_id)
        if not emp:
            return {
                "status": "not_found",
                "error": f"Employee '{employee_id}' was not found in the database. Please verify the ID or name."
            }

        balance = LeaveBalance.objects.filter(employee=emp, year=int(year)).first()
        if not balance:
            return {
                "status": "not_found",
                "employee_id": emp.employee_id,
                "employee_name": emp.name,
                "error": f"No leave balance record found for {emp.employee_id} ({emp.name}) for year {year}."
            }

        return {
            "status": "success",
            "employee_id": emp.employee_id,
            "employee_name": emp.name,
            "department": emp.department,
            "year": balance.year,
            "balances": {
                "annual_leave": float(balance.annual_leave),
                "sick_leave": float(balance.sick_leave),
                "casual_leave": float(balance.casual_leave),
                "parental_leave": float(balance.parental_leave),
                "comp_off": float(balance.comp_off)
            }
        }
    except Exception as e:
        return {"status": "error", "error": f"Database error fetching leave balance: {str(e)}"}


def get_payslip(employee_id: str, month: str = "", year: int = 0) -> dict:
    """
    Fetch employee payslip details from PostgreSQL.
    Args:
        employee_id: Unique employee ID (e.g. 'EMP001') or employee name.
        month: Specific month name (e.g. 'August', 'September'). If omitted or empty, fetches latest payslip.
        year: Calendar year (e.g. 2026). If 0 or omitted, searches recent periods.
    """
    try:
        emp = _resolve_employee(employee_id)
        if not emp:
            return {
                "status": "not_found",
                "error": f"Employee '{employee_id}' was not found in the database. Please verify the ID or name."
            }

        qs = Payslip.objects.filter(employee=emp)
        if year and int(year) > 0:
            qs = qs.filter(year=int(year))
        if month and str(month).strip():
            qs = qs.filter(month__iexact=str(month).strip())

        payslip = qs.order_by('-year', '-disbursement_date').first()
        if not payslip:
            return {
                "status": "not_found",
                "employee_id": emp.employee_id,
                "employee_name": emp.name,
                "error": f"No payslip found for employee {emp.employee_id} ({emp.name}) matching month={month or 'latest'} year={year or 'all'}."
            }

        return {
            "status": "success",
            "employee_id": emp.employee_id,
            "employee_name": emp.name,
            "department": emp.department,
            "payslip": {
                "month": payslip.month,
                "year": payslip.year,
                "basic_salary": float(payslip.basic_salary),
                "hra": float(payslip.hra),
                "allowances": float(payslip.allowances),
                "gross_salary": float(payslip.gross_salary),
                "deductions": {
                    "tax": float(payslip.tax_deduction),
                    "provident_fund": float(payslip.pf_deduction),
                    "health_insurance": float(payslip.insurance_deduction),
                    "total": float(payslip.total_deductions)
                },
                "net_salary": float(payslip.net_salary),
                "currency": payslip.currency,
                "payment_status": payslip.payment_status,
                "disbursement_date": payslip.disbursement_date.strftime("%Y-%m-%d")
            }
        }
    except Exception as e:
        return {"status": "error", "error": f"Database error fetching payslip: {str(e)}"}


def get_hr_policy(topic: str) -> dict:
    """
    Fetch official company HR policies from PostgreSQL.
    Args:
        topic: Policy topic or keyword (e.g. 'remote work', 'sick leave', 'annual leave', 'maternity', 'expenses').
    """
    try:
        clean_topic = topic.strip()
        policy = HRPolicy.objects.filter(
            Q(policy_id__icontains=clean_topic) |
            Q(title__icontains=clean_topic) |
            Q(category__icontains=clean_topic) |
            Q(content__icontains=clean_topic)
        ).first()

        if policy:
            return {
                "status": "success",
                "policy_id": policy.policy_id,
                "title": policy.title,
                "category": policy.category,
                "content": policy.content
            }

        available_titles = list(HRPolicy.objects.values_list('title', flat=True))
        return {
            "status": "not_found",
            "error": f"No HR policy found matching '{topic}'.",
            "available_policies": available_titles
        }
    except Exception as e:
        return {"status": "error", "error": f"Database error fetching policy: {str(e)}"}


def calculate_leave_days(start_date: str, end_date: str, include_weekends: bool = False) -> dict:
    """
    Compute tool: Pure Python business day and calendar day calculation between two dates.
    Args:
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        include_weekends: Whether weekends are included in deductible leave. Defaults to False.
    """
    try:
        d_start = datetime.strptime(start_date.strip(), "%Y-%m-%d").date()
        d_end = datetime.strptime(end_date.strip(), "%Y-%m-%d").date()

        if d_start > d_end:
            return {
                "status": "invalid_dates",
                "error": f"start_date ({start_date}) cannot be after end_date ({end_date})."
            }

        total_days = (d_end - d_start).days + 1
        working_days = 0
        weekend_days = 0
        dates_breakdown = []

        curr = d_start
        while curr <= d_end:
            is_weekend = curr.weekday() in (5, 6)
            day_type = "weekend" if is_weekend else "business_day"
            if is_weekend:
                weekend_days += 1
            else:
                working_days += 1

            dates_breakdown.append({
                "date": curr.strftime("%Y-%m-%d"),
                "day_name": curr.strftime("%A"),
                "type": day_type
            })
            curr += timedelta(days=1)

        deductible_leave_days = total_days if include_weekends else working_days

        return {
            "status": "success",
            "start_date": start_date,
            "end_date": end_date,
            "total_calendar_days": total_days,
            "working_days": working_days,
            "weekend_days": weekend_days,
            "deductible_leave_days": deductible_leave_days,
            "weekends_included": include_weekends,
            "dates_breakdown": dates_breakdown
        }
    except ValueError as ve:
        return {
            "status": "error",
            "error": f"Invalid date format: {str(ve)}. Please provide dates in YYYY-MM-DD format."
        }
    except Exception as e:
        return {"status": "error", "error": f"Error calculating leave days: {str(e)}"}


def submit_leave_request(employee_id: str, leave_type: str, start_date: str, end_date: str, reason: str = "") -> dict:
    """
    Write tool: Submit and persist a leave request to PostgreSQL.
    Args:
        employee_id: Unique employee ID (e.g. 'EMP001') or name.
        leave_type: Leave category ('annual_leave', 'sick_leave', 'casual_leave', 'parental_leave', 'comp_off').
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        reason: Optional justification for the leave.
    """
    try:
        emp = _resolve_employee(employee_id)
        if not emp:
            return {
                "status": "not_found",
                "error": f"Employee '{employee_id}' not found in database. Cannot submit leave request."
            }

        calc_result = calculate_leave_days(start_date, end_date, include_weekends=False)
        if calc_result.get("status") != "success":
            return calc_result

        days_needed = calc_result["deductible_leave_days"]
        if days_needed <= 0:
            return {
                "status": "error",
                "error": "The requested period contains 0 working days (e.g. only weekends)."
            }

        norm_leave_type = leave_type.lower().strip().replace(" ", "_")
        current_year = datetime.now().year
        bal_obj = LeaveBalance.objects.filter(employee=emp, year=current_year).first()

        balance_note = ""
        if bal_obj and hasattr(bal_obj, norm_leave_type):
            current_balance = float(getattr(bal_obj, norm_leave_type))
            if current_balance < days_needed:
                return {
                    "status": "insufficient_balance",
                    "error": (
                        f"Insufficient leave balance: {emp.name} has {current_balance} days "
                        f"of {leave_type}, but requested {days_needed} working days."
                    )
                }
            balance_note = f"Remaining balance after approval will be {current_balance - days_needed} days."

        request_id = f"LR-{datetime.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
        d_start = datetime.strptime(start_date.strip(), "%Y-%m-%d").date()
        d_end = datetime.strptime(end_date.strip(), "%Y-%m-%d").date()

        req = LeaveRequest.objects.create(
            request_id=request_id,
            employee=emp,
            leave_type=leave_type,
            start_date=d_start,
            end_date=d_end,
            working_days_requested=days_needed,
            calendar_days=calc_result["total_calendar_days"],
            reason=reason or "Not provided",
            status="Pending Approval"
        )

        return {
            "status": "success",
            "message": f"Leave request {request_id} has been successfully submitted.",
            "request_id": request_id,
            "employee_id": emp.employee_id,
            "employee_name": emp.name,
            "leave_type": leave_type,
            "start_date": start_date,
            "end_date": end_date,
            "working_days": days_needed,
            "request_status": req.status,
            "balance_info": balance_note
        }
    except Exception as e:
        return {"status": "error", "error": f"Failed to submit leave request: {str(e)}"}


def get_current_datetime(timezone_str: str = "UTC") -> dict:
    """
    Live tool: Returns current real-time date, time, and day of week.
    """
    now = datetime.now()
    utcnow = datetime.utcnow()
    return {
        "status": "success",
        "current_date": now.strftime("%Y-%m-%d"),
        "current_time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "iso_timestamp": utcnow.isoformat() + "Z",
        "system_datetime_string": now.strftime("%A, %B %d, %Y %I:%M:%S %p")
    }


TOOL_REGISTRY = {
    "get_leave_balance": get_leave_balance,
    "get_payslip": get_payslip,
    "get_hr_policy": get_hr_policy,
    "calculate_leave_days": calculate_leave_days,
    "submit_leave_request": submit_leave_request,
    "get_current_datetime": get_current_datetime,
}

ALL_TOOLS = list(TOOL_REGISTRY.values())


def execute_tool(tool_name: str, arguments: dict):
    """Executes a registered tool with parsed arguments safely."""
    if tool_name not in TOOL_REGISTRY:
        return {
            "status": "error",
            "error": f"Unknown tool '{tool_name}'. Available tools: {list(TOOL_REGISTRY.keys())}"
        }

    func = TOOL_REGISTRY[tool_name]
    try:
        return func(**arguments)
    except TypeError as te:
        return {
            "status": "error",
            "error": f"Invalid arguments for tool '{tool_name}': {str(te)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failure while executing tool '{tool_name}': {str(e)}"
        }
