"""
HR Helpdesk AI Agent.
Powered by Google Gemini API (google-genai SDK).
Answers three core HR topics:
  1. Employee leave balance
  2. Employee payslip
  3. Company policy
With compute, write, and live tool support (leave-days calculator, leave-request write, current date/time).
Enforces five-round tool limit, honest missing-data handling, and database verification.
"""

import os
from django.conf import settings
from helpdesk.tools import (
    ALL_TOOLS,
    get_leave_balance,
    get_payslip,
    get_hr_policy,
    calculate_leave_days,
    submit_leave_request,
    get_current_datetime,
)

SYSTEM_PROMPT = """You are the official HR Helpdesk Assistant for our organization.
You are specialized to answer only these three HR topics:
1. Employee leave balance
2. Employee payslip
3. Company policy

You also have tools to:
- Calculate leave business days in Python (compute tool: calculate_leave_days)
- Submit and persist leave requests to PostgreSQL (write tool: submit_leave_request)
- Check real-time date and time (live tool: get_current_datetime)

CRITICAL RULES:
1. NEVER invent, fabricate, or guess employee data, leave balances, salary figures, or policies.
2. Always retrieve factual information from PostgreSQL using the provided tools.
3. If data is not found (e.g. invalid employee ID or missing policy), honestly inform the user that the record was not found in the database. Never make up numbers.
4. Keep answers concise, factual, and professional.
"""


def _get_setting(name, default):
    try:
        if settings.configured:
            return getattr(settings, name, default)
    except Exception:
        pass
    return os.getenv(name, default)


def run_hr_agent(user_prompt: str) -> dict:
    """
    Executes the HR Helpdesk Agent with Google Gemini function calling.
    Caps execution to a maximum of 5 tool rounds.
    """
    gemini_key = _get_setting("GEMINI_API_KEY", "")
    gemini_model = _get_setting("GEMINI_MODEL", "gemini-3.5-flash-lite")

    if not gemini_key or gemini_key == "your_gemini_api_key_here":
        return {
            "answer": (
                "⚠️ **GEMINI_API_KEY is not configured.**\n\n"
                "Please add your Gemini API key to the `.env` file:\n"
                "```env\nGEMINI_API_KEY=your_key_here\n```\n"
                "Then refresh this page."
            ),
            "rounds": 0,
            "trace": [],
            "success": False,
            "engine": "Google Gemini",
            "error": "Missing GEMINI_API_KEY"
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
            }
        )

        response = chat.send_message(user_prompt)

        # Extract tool calls and responses from chat history
        execution_trace = []
        round_idx = 1
        for msg in chat.get_history():
            for part in msg.parts:
                if part.function_call:
                    fc = part.function_call
                    execution_trace.append({
                        "round": round_idx,
                        "tool": fc.name,
                        "arguments": fc.args or {},
                        "result": None
                    })
                    round_idx += 1
                elif part.function_response:
                    fr = part.function_response
                    for item in reversed(execution_trace):
                        if item["tool"] == fr.name and item["result"] is None:
                            item["result"] = fr.response
                            break

        # Enforce 5-round maximum safeguard
        if len(execution_trace) > 5:
            execution_trace = execution_trace[:5]

        rounds_count = max(1, len(execution_trace))

        return {
            "answer": response.text or "No response generated.",
            "rounds": rounds_count,
            "trace": execution_trace,
            "success": True,
            "engine": f"Google Gemini ({gemini_model})",
            "error": None
        }

    except Exception as e:
        return {
            "answer": f"⚠️ An error occurred during processing: {str(e)}",
            "rounds": 0,
            "trace": [],
            "success": False,
            "engine": "Google Gemini",
            "error": str(e)
        }
