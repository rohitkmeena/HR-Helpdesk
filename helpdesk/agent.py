
"""
HR Helpdesk AI Agent.
Powered by Google Gemini API (google-genai SDK).

Supports:
1. Employee leave balance
2. Employee payslip
3. Company HR policies
4. Leave-day calculation
5. Leave-request submission
6. Existing leave-request status lookup
7. Current date and time
"""

import os
import time

from google.genai import errors
from django.conf import settings

from helpdesk.tools import (
    ALL_TOOLS,
    get_leave_balance,
    get_payslip,
    get_hr_policy,
    calculate_leave_days,
    submit_leave_request,
    get_leave_request_status,
    get_current_datetime,
)


SYSTEM_PROMPT = """You are the official HR Helpdesk Assistant.

You help employees with:
1. Employee leave balances
2. Employee payslips
3. Company HR policies
4. Leave-day calculations
5. Submitting leave requests
6. Checking the status of existing leave requests
7. Current date and time

AVAILABLE TOOLS:
- get_leave_balance: Retrieve an employee's leave balances.
- get_payslip: Retrieve an employee's payslip.
- get_hr_policy: Retrieve company HR policies.
- calculate_leave_days: Calculate calendar and working days.
- submit_leave_request: Submit and save a new leave request.
- get_leave_request_status: Find an existing leave request by
  its request ID and retrieve its current status.
- get_current_datetime: Retrieve the current system date and time.

CRITICAL RULES:
1. NEVER invent employee data, leave balances, salaries, policies,
   request IDs, or request statuses.
2. Always retrieve factual information from the database using tools.
3. When checking a leave-request status, call
   get_leave_request_status with the supplied request ID.
4. Do not submit a new leave request when the user only asks to
   check an existing request.
5. If a request ID is missing, ask the user to provide it.
6. If a request is not found, explain that the database has no
   matching record. Do not guess its status.
7. Do not claim that a leave request was submitted unless the
   submission tool returns success.
8. A request marked Pending Approval is not an approved request.
9. Do not claim that a leave balance has been deducted unless
   the database confirms the deduction.
10. Ask for an employee ID or full name when needed for an
    employee-specific lookup.
11. Keep answers concise, factual, and professional.
12. Only answer questions related to the supported HR functions.
"""


def _get_setting(name, default):
    """Read a setting from Django or the environment."""
    try:
        if settings.configured:
            return getattr(settings, name, default)
    except Exception:
        pass

    return os.getenv(name, default)


def run_hr_agent(user_prompt: str) -> dict:
    """
    Execute the HR Helpdesk agent with Gemini function calling.
    Preserve the existing retry behavior and response structure.
    """
    gemini_key = _get_setting("GEMINI_API_KEY", "")
    gemini_model = _get_setting(
        "GEMINI_MODEL",
        "gemini-3.5-flash-lite",
    )

    if (
        not gemini_key
        or gemini_key == "your_gemini_api_key_here"
    ):
        return {
            "answer": (
                "GEMINI_API_KEY is not configured. "
                "Please add your Gemini API key to the .env file "
                "and refresh the page."
            ),
            "rounds": 0,
            "trace": [],
            "success": False,
            "engine": "Google Gemini",
            "error": "Missing GEMINI_API_KEY",
        }

    try:
        from google import genai

        client = genai.Client(api_key=gemini_key)

        chat = client.chats.create(
            model=gemini_model,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "tools": ALL_TOOLS,
                "temperature": 0.1,
            },
        )

        response = None

        # Retry temporary Gemini 503 errors up to three attempts.
        for attempt in range(3):
            try:
                response = chat.send_message(user_prompt)
                break
            except errors.APIError as exc:
                if exc.code != 503 or attempt == 2:
                    raise

                time.sleep(2 ** (attempt + 1))

        if response is None:
            raise RuntimeError(
                "Gemini did not return a response."
            )

        # Collect tool calls and their returned results.
        execution_trace = []
        round_idx = 1

        for msg in chat.get_history():
            for part in msg.parts:
                if part.function_call:
                    function_call = part.function_call

                    execution_trace.append({
                        "round": round_idx,
                        "tool": function_call.name,
                        "arguments": function_call.args or {},
                        "result": None,
                    })
                    round_idx += 1

                elif part.function_response:
                    function_response = part.function_response

                    for item in reversed(execution_trace):
                        if (
                            item["tool"] == function_response.name
                            and item["result"] is None
                        ):
                            item["result"] = function_response.response
                            break

        # Preserve the existing five-round trace limit.
        if len(execution_trace) > 5:
            execution_trace = execution_trace[:5]

        rounds_count = max(1, len(execution_trace))

        return {
            "answer": response.text or "No response generated.",
            "rounds": rounds_count,
            "trace": execution_trace,
            "success": True,
            "engine": f"Google Gemini ({gemini_model})",
            "error": None,
        }

    except Exception as e:
        return {
            "answer": (
                f"An error occurred during processing: {str(e)}"
            ),
            "rounds": 0,
            "trace": [],
            "success": False,
            "engine": "Google Gemini",
            "error": str(e),
        }
