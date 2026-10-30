
from pathlib import Path

import frappe
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def process_policy_pdf(file_url: str):
    """Load an uploaded Frappe PDF and split it into chunks."""

    file_doc = frappe.db.get_value(
        "File",
        {"file_url": file_url},
        ["file_url", "is_private"],
        as_dict=True,
    )

    if not file_doc:
        frappe.throw(f"Frappe File record not found: {file_url}")

    # Resolve through Frappe's File document.
    file_record = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_record.get_full_path()

    if not Path(file_path).is_file():
        frappe.throw("The uploaded policy PDF could not be found on disk.")

    loader = PyPDFLoader(str(file_path))
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )

    chunks = splitter.split_documents(documents)

    if not chunks:
        frappe.throw(
            "No readable text found in this PDF. "
            "It may be scanned and require OCR."
        )

    return chunks
