import frappe
from hr_policy_assistant.rag import answer_question


@frappe.whitelist()
def ask(question: str):
    question = (question or "").strip()
    if not question:
        frappe.throw("Please enter a question.")
    if len(question) > 500:
        frappe.throw("Question is too long.")

    try:
        return answer_question(question)
    except Exception:
        frappe.log_error(title="HR Policy Assistant error")
        frappe.throw("Sorry, something went wrong. Please try again.")