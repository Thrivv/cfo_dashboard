import csv

import fitz  # PyMuPDF


def parse_pdf(path: str) -> str:
    """Extract text from PDF using PyMuPDF."""
    doc = fitz.open(path)
    texts = []
    for page in doc:
        texts.append(page.get_text("text"))
    return "\n".join(texts)


def parse_csv(path: str) -> list[str]:
    """Parse CSV into a Markdown table."""
    with open(path, "r") as f:
        reader = csv.reader(f)
        header = next(reader)
        table = ["| " + " | ".join(header) + " |"]
        table.append("|" + "---|" * len(header))
        for row in reader:
            table.append("| " + " | ".join(row) + " |")
        return ["\n".join(table)]
