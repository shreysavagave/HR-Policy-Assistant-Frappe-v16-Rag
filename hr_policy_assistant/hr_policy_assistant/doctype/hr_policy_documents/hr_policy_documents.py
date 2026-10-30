# Copyright (c) 2026, Shrey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class HRPolicyDocuments(Document):
    def on_update(self):
        frappe.enqueue(
            "hr_policy_assistant.rag.rebuild_index",
            queue="long",
            timeout=1800,
            job_id="hr_policy_rebuild_index",
            deduplicate=True,
            enqueue_after_commit=True,
        )
