import pdfplumber

def read_pdf(pdf_file_path):
    with pdfplumber.open(pdf_file_path) as pdf:
        text = ' '.join([page.extract_text() for page in pdf.pages if page.extract_text() != None])
    return text