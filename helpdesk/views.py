"""
Views for HR-Helpdesk single Q&A page.
Handles both standard form submissions and asynchronous fetch requests.
"""

import os
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.db import connection
from helpdesk.agent import run_hr_agent

def check_db_connection():
    try:
        connection.ensure_connection()
        return True, "Connected"
    except Exception as e:
        return False, str(e)

@require_http_methods(["GET", "POST"])
def index(request):
    db_ok, db_msg = check_db_connection()
    gemini_key = getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
    gemini_configured = bool(gemini_key and gemini_key != "your_gemini_api_key_here")

    if request.method == "POST":
        if request.content_type == "application/json":
            try:
                body = json.loads(request.body.decode("utf-8"))
                question = body.get("question", "").strip()
            except Exception:
                question = ""
        else:
            question = request.POST.get("question", "").strip()

        if not question:
            response_data = {
                "answer": "Please enter an HR question.",
                "rounds": 0,
                "trace": [],
                "success": False,
                "error": "Empty question"
            }
        else:
            response_data = run_hr_agent(question)

        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.content_type == "application/json":
            return JsonResponse({
                "question": question,
                **response_data
            })

        context = {
            "db_ok": db_ok,
            "db_msg": db_msg,
            "gemini_configured": gemini_configured,
            "question": question,
            "result": response_data,
        }
        return render(request, "helpdesk/index.html", context)

    context = {
        "db_ok": db_ok,
        "db_msg": db_msg,
        "gemini_configured": gemini_configured,
        "question": "",
        "result": None,
    }
    return render(request, "helpdesk/index.html", context)
