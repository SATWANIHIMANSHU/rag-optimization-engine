from pathlib import Path
from pypdf import PdfReader

DOCUMENTS_DIR = Path("data/documents")


def load_text_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def load_pdf_file(file_path):
    reader = PdfReader(file_path)

    pages = []
    pages_without_text = 0

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text()

        if text and text.strip():
            pages.append({
                "page": page_number,
                "text": text
            })
        else:
            pages_without_text += 1

    print(f"Total PDF pages: {len(reader.pages)}")
    print(f"Pages with extracted text: {len(pages)}")
    print(f"Pages without extracted text: {pages_without_text}")

    return pages


def load_documents():
    documents = []

    if not DOCUMENTS_DIR.exists():
        return documents

    for file_path in DOCUMENTS_DIR.iterdir():

        if not file_path.is_file():
            continue

        if file_path.suffix.lower() == ".txt":

            text = load_text_file(file_path)

            documents.append({
                "text": text,
                "source": file_path.name,
                "type": "txt"
            })

        elif file_path.suffix.lower() == ".pdf":

            pages = load_pdf_file(file_path)

            documents.append({
                "pages": pages,
                "source": file_path.name,
                "type": "pdf"
            })

    return documents