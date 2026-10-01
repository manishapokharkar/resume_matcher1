import os
import fitz
from docx import Document


def extract_pdf_text(file_path):

    text = ""

    document = fitz.open(file_path)

    for page in document:
        text += page.get_text()

    document.close()

    return text


def extract_docx_text(file_path):

    document = Document(file_path)

    text = []

    for paragraph in document.paragraphs:
        text.append(paragraph.text)

    return "\n".join(text)


def extract_resume_text(file_path):

    extension = os.path.splitext(
        file_path
    )[1].lower()

    if extension == ".pdf":

        return extract_pdf_text(file_path)

    elif extension == ".docx":

        return extract_docx_text(file_path)

    else:

        raise ValueError(
            f"Unsupported file type: {extension}"
        )


if __name__ == "__main__":

    folder = "email_resumes"

    for filename in os.listdir(folder):

        file_path = os.path.join(
            folder,
            filename
        )

        try:

            text = extract_resume_text(
                file_path
            )

            print("\n================================")
            print("FILE:", filename)
            print("================================\n")

            print(text[:3000])

        except Exception as error:

            print(
                f"Error reading {filename}: {error}"
            )