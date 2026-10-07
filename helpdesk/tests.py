"""
Unit and integration tests for HR-Helpdesk tools, models, agent, and views.
"""

from datetime import date
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock

from helpdesk.models import Employee, LeaveBalance, Payslip, HRPolicy, LeaveRequest
from helpdesk.tools import (
    get_leave_balance,
    get_payslip,
    get_hr_policy,
    calculate_leave_days,
    submit_leave_request,
    get_current_datetime,
    execute_tool,
    TOOL_REGISTRY,
    ALL_TOOLS,
)
from helpdesk.agent import run_hr_agent


class HRDatabaseToolsTestCase(TestCase):
    def setUp(self):
        self.emp = Employee.objects.create(
            employee_id="EMP001",
            name="Alice Johnson",
            email="alice@example.com",
            department="Engineering",
            designation="Staff Engineer",
            joining_date=date(2021, 4, 12),
            manager="EMP005",
            status="Active"
        )
        self.balance = LeaveBalance.objects.create(
            employee=self.emp,
            year=2026,
            annual_leave=Decimal("16.5"),
            sick_leave=Decimal("9.0"),
            casual_leave=Decimal("4.0"),
            parental_leave=Decimal("60.0"),
            comp_off=Decimal("2.0")
        )
        self.payslip = Payslip.objects.create(
            employee=self.emp,
            month="September",
            year=2026,
            basic_salary=Decimal("8500.00"),
            hra=Decimal("2550.00"),
            allowances=Decimal("1275.00"),
            gross_salary=Decimal("12325.00"),
            tax_deduction=Decimal("2218.50"),
            pf_deduction=Decimal("510.00"),
            insurance_deduction=Decimal("120.00"),
            total_deductions=Decimal("2848.50"),
            net_salary=Decimal("9476.50"),
            currency="USD",
            payment_status="Paid",
            disbursement_date=date(2026, 9, 30)
        )
        self.policy = HRPolicy.objects.create(
            policy_id="POL_REMOTE_WORK",
            title="Remote Work & Hybrid Workplace Policy",
            category="Workplace Guidelines",
            content="Employees may work remotely up to 3 days per week with core hours 10 AM to 4 PM."
        )

    def test_get_leave_balance_existing_employee(self):
        res = get_leave_balance("EMP001")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["employee_name"], "Alice Johnson")
        self.assertEqual(res["balances"]["annual_leave"], 16.5)

    def test_get_leave_balance_by_name(self):
        res = get_leave_balance("Alice Johnson")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["employee_id"], "EMP001")

    def test_get_leave_balance_not_found(self):
        res = get_leave_balance("EMP999")
        self.assertEqual(res["status"], "not_found")
        self.assertIn("not found in the database", res["error"])

    def test_get_payslip_existing(self):
        res = get_payslip("EMP001", month="September", year=2026)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["payslip"]["net_salary"], 9476.50)
        self.assertEqual(res["payslip"]["month"], "September")

    def test_get_payslip_not_found(self):
        res = get_payslip("EMP001", month="January", year=2025)
        self.assertEqual(res["status"], "not_found")

    def test_get_hr_policy_existing(self):
        res = get_hr_policy("remote work")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["policy_id"], "POL_REMOTE_WORK")
        self.assertIn("remotely up to 3 days", res["content"])

    def test_get_hr_policy_not_found(self):
        res = get_hr_policy("space travel policy")
        self.assertEqual(res["status"], "not_found")
        self.assertIn("available_policies", res)

    def test_submit_leave_request_success(self):
        res = submit_leave_request("EMP001", "annual_leave", "2026-10-12", "2026-10-14", "Vacation")
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["request_id"].startswith("LR-"))
        self.assertEqual(res["working_days"], 3)
        self.assertEqual(LeaveRequest.objects.count(), 1)
        req = LeaveRequest.objects.first()
        self.assertEqual(req.employee, self.emp)
        self.assertEqual(req.working_days_requested, 3)

    def test_submit_leave_request_insufficient_balance(self):
        self.balance.annual_leave = Decimal("1.0")
        self.balance.save()

        res = submit_leave_request("EMP001", "annual_leave", "2026-10-12", "2026-10-14", "Trip")
        self.assertEqual(res["status"], "insufficient_balance")
        self.assertEqual(LeaveRequest.objects.count(), 0)


class HRDateToolsTestCase(TestCase):
    def test_calculate_leave_days_business_week(self):
        result = calculate_leave_days("2026-10-12", "2026-10-16")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["working_days"], 5)
        self.assertEqual(result["weekend_days"], 0)
        self.assertEqual(result["total_calendar_days"], 5)
        self.assertEqual(result["deductible_leave_days"], 5)

    def test_calculate_leave_days_across_weekend(self):
        result = calculate_leave_days("2026-10-16", "2026-10-19")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["working_days"], 2)
        self.assertEqual(result["weekend_days"], 2)
        self.assertEqual(result["total_calendar_days"], 4)
        self.assertEqual(result["deductible_leave_days"], 2)

    def test_calculate_leave_days_with_weekends_included(self):
        result = calculate_leave_days("2026-10-16", "2026-10-19", include_weekends=True)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["deductible_leave_days"], 4)

    def test_calculate_leave_days_invalid_order(self):
        result = calculate_leave_days("2026-10-20", "2026-10-15")
        self.assertEqual(result["status"], "invalid_dates")

    def test_get_current_datetime(self):
        result = get_current_datetime()
        self.assertEqual(result["status"], "success")
        self.assertIn("current_date", result)
        self.assertIn("day_of_week", result)

    def test_execute_tool_unknown_tool(self):
        result = execute_tool("non_existent_tool", {})
        self.assertEqual(result["status"], "error")
        self.assertIn("Unknown tool", result["error"])

    def test_tool_schemas_registered(self):
        self.assertEqual(len(ALL_TOOLS), 6)
        self.assertEqual(len(TOOL_REGISTRY), 6)


class HRAgentTestCase(TestCase):
    def test_agent_missing_key(self):
        with patch.dict('os.environ', {'GEMINI_API_KEY': ''}):
            with patch('django.conf.settings.GEMINI_API_KEY', ''):
                res = run_hr_agent("What is my leave balance?")
                self.assertFalse(res["success"])
                self.assertIn("GEMINI_API_KEY is not configured", res["answer"])

    @patch('google.genai.Client')
    def test_gemini_agent_direct_response(self, mock_genai_client):
        mock_client = MagicMock()
        mock_genai_client.return_value = mock_client
        mock_chat = MagicMock()
        mock_resp = MagicMock(text="Annual leave is 20 days per year.")
        mock_chat.send_message.return_value = mock_resp
        mock_chat.get_history.return_value = []
        mock_client.chats.create.return_value = mock_chat

        with patch.dict('os.environ', {'GEMINI_API_KEY': 'AQ_test'}):
            with patch('django.conf.settings.GEMINI_API_KEY', 'AQ_test'):
                res = run_hr_agent("What is the annual leave policy?")
                self.assertTrue(res["success"])
                self.assertEqual(res["answer"], "Annual leave is 20 days per year.")
                self.assertIn("Google Gemini", res["engine"])
                self.assertEqual(len(res["trace"]), 0)

    @patch('google.genai.Client')
    def test_gemini_agent_function_call_trace(self, mock_genai_client):
        mock_client = MagicMock()
        mock_genai_client.return_value = mock_client
        mock_chat = MagicMock()
        mock_resp = MagicMock(text="Alice Johnson has 16.5 days of annual leave.")

        # Simulate function call in chat history
        mock_fc = MagicMock()
        mock_fc.function_call.name = "get_leave_balance"
        mock_fc.function_call.args = {"employee_id": "EMP001"}
        mock_fc.function_response = None

        mock_fr = MagicMock()
        mock_fr.function_call = None
        mock_fr.function_response.name = "get_leave_balance"
        mock_fr.function_response.response = {"status": "success", "balances": {"annual_leave": 16.5}}

        mock_chat.get_history.return_value = [
            MagicMock(parts=[mock_fc]),
            MagicMock(parts=[mock_fr]),
        ]
        mock_chat.send_message.return_value = mock_resp
        mock_client.chats.create.return_value = mock_chat

        with patch.dict('os.environ', {'GEMINI_API_KEY': 'AQ_test'}):
            with patch('django.conf.settings.GEMINI_API_KEY', 'AQ_test'):
                res = run_hr_agent("What is the leave balance for EMP001?")
                self.assertTrue(res["success"])
                self.assertEqual(len(res["trace"]), 1)
                self.assertEqual(res["trace"][0]["tool"], "get_leave_balance")
                self.assertEqual(res["trace"][0]["arguments"]["employee_id"], "EMP001")


class WebPageTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_get_page_renders_ok(self):
        response = self.client.get(reverse('helpdesk_index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "HR Helpdesk")
        self.assertContains(response, "Ask an HR Question")

    def test_post_empty_question(self):
        response = self.client.post(reverse('helpdesk_index'), {"question": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter an HR question.")

    def test_ajax_post_empty_question(self):
        response = self.client.post(
            reverse('helpdesk_index'),
            data='{"question": ""}',
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "Empty question")
