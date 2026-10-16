
"""
HR-Helpdesk Tools.

Provides employee leave balances, payslips, HR policies,
leave-day calculations, leave-request submission, leave-request
status lookup, and current date/time.
"""

import uuid
from datetime import datetime, timedelta

from django.db.models import Q

from helpdesk.models import (
    Employee,
    LeaveBalance,
    Payslip,
    HRPolicy,
    LeaveRequest,
)


def _resolve_employee(employee_id_or_name: str) -> Employee | None:
    """Find an employee by employee ID or name."""
    if not employee_id_or_name or not employee_id_or_name.strip():
        return None

    clean_query = employee_id_or_name.strip()

    employee = Employee.objects.filter(
        employee_id__iexact=clean_query
    ).first()

    if employee:
        return employee

    return Employee.objects.filter(
        name__icontains=clean_query
    ).first()


def get_leave_balance(employee_id: str, year: int = 2026) -> dict:
    """Fetch an employee's leave balances for a given year."""
    try:
        employee = _resolve_employee(employee_id)

        if not employee:
            return {
                "status": "not_found",
                "error": (
                    f"Employee '{employee_id}' was not found. "
                    "Please verify the ID or name."
                ),
            }

        balance = LeaveBalance.objects.filter(
            employee=employee,
            year=int(year),
        ).first()

        if not balance:
            return {
                "status": "not_found",
                "employee_id": employee.employee_id,
                "employee_name": employee.name,
                "error": (
                    f"No leave balance found for "
                    f"{employee.employee_id} in {year}."
                ),
            }

        return {
            "status": "success",
            "employee_id": employee.employee_id,
            "employee_name": employee.name,
            "department": employee.department,
            "year": balance.year,
            "balances": {
                "annual_leave": float(balance.annual_leave),
                "sick_leave": float(balance.sick_leave),
                "casual_leave": float(balance.casual_leave),
                "parental_leave": float(balance.parental_leave),
                "comp_off": float(balance.comp_off),
            },
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Database error fetching leave balance: {str(e)}",
        }


def get_payslip(
    employee_id: str,
    month: str = "",
    year: int = 0,
) -> dict:
    """Fetch an employee's payslip."""
    try:
        employee = _resolve_employee(employee_id)

        if not employee:
            return {
                "status": "not_found",
                "error": f"Employee '{employee_id}' was not found.",
            }

        query = Payslip.objects.filter(employee=employee)

        if year and int(year) > 0:
            query = query.filter(year=int(year))

        if month and str(month).strip():
            query = query.filter(month__iexact=str(month).strip())

        payslip = query.order_by(
            "-year",
            "-disbursement_date",
        ).first()

        if not payslip:
            return {
                "status": "not_found",
                "employee_id": employee.employee_id,
                "employee_name": employee.name,
                "error": (
                    f"No matching payslip found for "
                    f"{employee.employee_id}."
                ),
            }

        return {
            "status": "success",
            "employee_id": employee.employee_id,
            "employee_name": employee.name,
            "department": employee.department,
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
                    "health_insurance": float(
                        payslip.insurance_deduction
                    ),
                    "total": float(payslip.total_deductions),
                },
                "net_salary": float(payslip.net_salary),
                "currency": payslip.currency,
                "payment_status": payslip.payment_status,
                "disbursement_date": (
                    payslip.disbursement_date.strftime("%Y-%m-%d")
                ),
            },
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Database error fetching payslip: {str(e)}",
        }


def get_hr_policy(topic: str) -> dict:
    """Fetch a company HR policy by topic or keyword."""
    try:
        clean_topic = topic.strip()

        policy = HRPolicy.objects.filter(
            Q(policy_id__icontains=clean_topic)
            | Q(title__icontains=clean_topic)
            | Q(category__icontains=clean_topic)
            | Q(content__icontains=clean_topic)
        ).first()

        if policy:
            return {
                "status": "success",
                "policy_id": policy.policy_id,
                "title": policy.title,
                "category": policy.category,
                "content": policy.content,
            }

        available_titles = list(
            HRPolicy.objects.values_list("title", flat=True)
        )

        return {
            "status": "not_found",
            "error": f"No HR policy found matching '{topic}'.",
            "available_policies": available_titles,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Database error fetching policy: {str(e)}",
        }


def calculate_leave_days(
    start_date: str,
    end_date: str,
    include_weekends: bool = False,
) -> dict:
    """Calculate calendar days and working days between two dates."""
    try:
        start = datetime.strptime(
            start_date.strip(), "%Y-%m-%d"
        ).date()

        end = datetime.strptime(
            end_date.strip(), "%Y-%m-%d"
        ).date()

        if start > end:
            return {
                "status": "invalid_dates",
                "error": "The start date cannot be after the end date.",
            }

        total_days = (end - start).days + 1
        working_days = 0
        weekend_days = 0
        dates_breakdown = []

        current = start

        while current <= end:
            is_weekend = current.weekday() in (5, 6)

            if is_weekend:
                weekend_days += 1
                day_type = "weekend"
            else:
                working_days += 1
                day_type = "business_day"

            dates_breakdown.append({
                "date": current.isoformat(),
                "day_name": current.strftime("%A"),
                "type": day_type,
            })

            current += timedelta(days=1)

        deductible_days = (
            total_days if include_weekends else working_days
        )

        return {
            "status": "success",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "total_calendar_days": total_days,
            "working_days": working_days,
            "weekend_days": weekend_days,
            "deductible_leave_days": deductible_days,
            "weekends_included": include_weekends,
            "dates_breakdown": dates_breakdown,
        }

    except ValueError as e:
        return {
            "status": "error",
            "error": (
                f"Invalid date: {str(e)}. "
                "Use YYYY-MM-DD format."
            ),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Error calculating leave days: {str(e)}",
        }


def submit_leave_request(
    employee_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: str = "",
) -> dict:
    """Create and save a leave request."""
    try:
        employee = _resolve_employee(employee_id)

        if not employee:
            return {
                "status": "not_found",
                "error": (
                    f"Employee '{employee_id}' was not found. "
                    "Cannot submit leave request."
                ),
            }

        calculation = calculate_leave_days(
            start_date,
            end_date,
            include_weekends=False,
        )

        if calculation.get("status") != "success":
            return calculation

        days_needed = calculation["deductible_leave_days"]

        if days_needed <= 0:
            return {
                "status": "error",
                "error": "The requested period contains no working days.",
            }

        normalized_type = (
            leave_type.lower().strip().replace(" ", "_")
        )

        valid_types = {
            "annual_leave",
            "sick_leave",
            "casual_leave",
            "parental_leave",
            "comp_off",
        }

        if normalized_type not in valid_types:
            return {
                "status": "error",
                "error": (
                    f"Invalid leave type '{leave_type}'. "
                    f"Allowed types: {sorted(valid_types)}"
                ),
            }

        current_year = datetime.now().year

        balance = LeaveBalance.objects.filter(
            employee=employee,
            year=current_year,
        ).first()

        balance_note = ""

        if balance:
            current_balance = float(
                getattr(balance, normalized_type)
            )

            if current_balance < days_needed:
                return {
                    "status": "insufficient_balance",
                    "error": (
                        f"{employee.name} has {current_balance} days "
                        f"of {normalized_type}, but "
                        f"{days_needed} days were requested."
                    ),
                }

            balance_note = (
                "Remaining balance after approval will be "
                f"{current_balance - days_needed} days."
            )

        start = datetime.strptime(
            start_date.strip(), "%Y-%m-%d"
        ).date()

        end = datetime.strptime(
            end_date.strip(), "%Y-%m-%d"
        ).date()

        request_id = (
            f"LR-{datetime.now().strftime('%Y%m')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        leave_request = LeaveRequest.objects.create(
            request_id=request_id,
            employee=employee,
            leave_type=normalized_type,
            start_date=start,
            end_date=end,
            working_days_requested=days_needed,
            calendar_days=calculation["total_calendar_days"],
            reason=reason or "Not provided",
            status="Pending Approval",
        )

        return {
            "status": "success",
            "message": (
                f"Leave request {request_id} "
                "has been successfully submitted."
            ),
            "request_id": request_id,
            "employee_id": employee.employee_id,
            "employee_name": employee.name,
            "leave_type": normalized_type,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "working_days": days_needed,
            "request_status": leave_request.status,
            "balance_info": balance_note,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to submit leave request: {str(e)}",
        }


def get_leave_request_status(request_id: str) -> dict:
    """Look up an existing leave request by its reference ID."""
    try:
        clean_id = request_id.strip()

        if not clean_id:
            return {
                "status": "error",
                "error": "Please provide a leave request ID.",
            }

        leave_request = (
            LeaveRequest.objects.filter(
                request_id__iexact=clean_id
            )
            .select_related("employee")
            .first()
        )

        if not leave_request:
            return {
                "status": "not_found",
                "error": (
                    f"No leave request found with ID '{clean_id}'."
                ),
            }

        return {
            "status": "success",
            "request_id": leave_request.request_id,
            "employee_id": leave_request.employee.employee_id,
            "employee_name": leave_request.employee.name,
            "leave_type": leave_request.leave_type,
            "start_date": leave_request.start_date.isoformat(),
            "end_date": leave_request.end_date.isoformat(),
            "working_days": leave_request.working_days_requested,
            "reason": leave_request.reason,
            "request_status": leave_request.status,
            "submitted_at": leave_request.submitted_at.isoformat(),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": (
                f"Failed to retrieve leave request status: {str(e)}"
            ),
        }


def get_current_datetime(timezone_str: str = "UTC") -> dict:
    """Return the current system date and time."""
    now = datetime.now()
    utc_now = datetime.utcnow()

    return {
        "status": "success",
        "current_date": now.strftime("%Y-%m-%d"),
        "current_time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "iso_timestamp": utc_now.isoformat() + "Z",
        "system_datetime_string": now.strftime(
            "%A, %B %d, %Y %I:%M:%S %p"
        ),
    }


TOOL_REGISTRY = {
    "get_leave_balance": get_leave_balance,
    "get_payslip": get_payslip,
    "get_hr_policy": get_hr_policy,
    "calculate_leave_days": calculate_leave_days,
    "submit_leave_request": submit_leave_request,
    "get_leave_request_status": get_leave_request_status,
    "get_current_datetime": get_current_datetime,
}

ALL_TOOLS = list(TOOL_REGISTRY.values())


def execute_tool(tool_name: str, arguments: dict):
    """Execute a registered tool with parsed arguments."""
    if tool_name not in TOOL_REGISTRY:
        return {
            "status": "error",
            "error": (
                f"Unknown tool '{tool_name}'. "
                f"Available tools: {list(TOOL_REGISTRY.keys())}"
            ),
        }

    function = TOOL_REGISTRY[tool_name]

    try:
        return function(**arguments)

    except TypeError as e:
        return {
            "status": "error",
            "error": (
                f"Invalid arguments for tool '{tool_name}': {str(e)}"
            ),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": (
                f"Failure while executing tool '{tool_name}': {str(e)}"
            ),
        }
