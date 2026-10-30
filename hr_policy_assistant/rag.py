import shutil
import frappe

# Confirm the exact model IDs in Google AI Studio, as names change often.
LLM_MODEL = "gemini-3.5-flash-lite"
EMBEDDING_MODEL = "models/gemini-embedding-001"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
TOP_K = 4

# Replace "policies" with the fieldname of your child table
CHILD_TABLE_FIELD = "hr_policy_documents"
SETTINGS_DOCTYPE = "HR Pollicy Assistant Settings"

def _api_key():
    settings = frappe.get_single(SETTINGS_DOCTYPE)
    key = settings.get_password("gemini_api_key", raise_exception=False)
    if not key:
        frappe.throw(f"Gemini API key is missing in {SETTINGS_DOCTYPE}")
    return key


def _index_path():
    return frappe.get_site_path("private", "hr_policy_index")


def _embeddings():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL, google_api_key=_api_key()
    )


def rebuild_index():
    """Read all PDFs from the DocType, chunk, embed, save FAISS index."""
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_community.vectorstores import FAISS
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    doc = frappe.get_single("HR Policy Documents")
    pages = []

    for row in doc.get(CHILD_TABLE_FIELD) or []:
        if not row.file or not row.file.lower().endswith(".pdf"):
            continue

        file_doc = frappe.get_doc("File", {"file_url": row.file})
        loaded = PyPDFLoader(file_doc.get_full_path()).load()

        for p in loaded:
            p.metadata = {
                "policy_title": row.policy_title,
                "page": p.metadata.get("page", 0) + 1,
            }
        pages.extend(loaded)

    shutil.rmtree(_index_path(), ignore_errors=True)
    if not pages:
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(pages)

    store = FAISS.from_documents(chunks, _embeddings())
    store.save_local(_index_path())


def answer_question(question: str) -> dict:
    import os
    from langchain_community.vectorstores import FAISS
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI

    if not os.path.exists(_index_path()):
        return {
            "answer": "No policy documents have been indexed yet. Please contact HR.",
            "sources": [],
        }

    store = FAISS.load_local(
        _index_path(), _embeddings(), allow_dangerous_deserialization=True
    )
    docs = store.similarity_search(question, k=TOP_K)

    context = "\n\n".join(
        f"[{d.metadata['policy_title']}, page {d.metadata['page']}]\n{d.page_content}"
        for d in docs
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an HR Policy Assistant for our company. "
            "Answer ONLY using the context below. "
            "If the answer is not in the context, say you could not find it "
            "in the policy documents and suggest contacting HR. "
            "Be concise and mention which policy the answer comes from.\n\n"
            "Context:\n{context}",
        ),
        ("human", "{question}"),
    ])

    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL, google_api_key=_api_key(), temperature=0
    )
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question})

    sources = sorted({
        f"{d.metadata['policy_title']} (p.{d.metadata['page']})" for d in docs
    })
    return {"answer": answer, "sources": sources}