import sys

from utils.pipeline import query_rag


def select_template(query: str) -> str:
    query_lower = query.lower()
    if "warning" in query_lower and (
        "account receivable" in query_lower or "receivables" in query_lower
    ):
        return "ar_warning_summary"
    if "warning" in query_lower and (
        "account payable" in query_lower or "payables" in query_lower
    ):
        return "ap_warning_summary"
    if "opportunity" in query_lower and (
        "account receivable" in query_lower or "receivables" in query_lower
    ):
        return "ar_opportunity_summary"
    if "opportunity" in query_lower and (
        "account payable" in query_lower or "payables" in query_lower
    ):
        return "ap_opportunity_summary"
    return "qa_template"


def query_documents(query: str):
    template_name = select_template(query)
    return query_rag(query, template_name=template_name)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:])
    if not query:
        query = input("Enter query: ")
    result = query_documents(query)
    print(result)
