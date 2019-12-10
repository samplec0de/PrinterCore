from PyPDF2 import PdfFileReader
from pathlib import Path

class PrinterFileException(Exception):
    pass

class PrinterFile:
    pdf = None
    file_type = None
    file = None
    name = None
    path = None
    extension = None

    def __init__(self, path):
        self.path = path
        self.file = Path(path)
        if not self.file.exists() or not self.file.is_file():
            raise PrinterFileException("File does not exist")
        self.name = self.file.name
        self.extension = self.name.split('.')[-1].lower()
        supported_extensions = ["pdf"]
        if self.extension not in supported_extensions:
            raise PrinterFileException("File extension is not supported")
        if self.extension == "pdf":
            self.file_type = 'pdf'
            self.load_pdf()

    def get_pages_count(self):
        if self.file_type == 'pdf':
            return self.pdf.getNumPages()

    def load_pdf(self):
        self.pdf = PdfFileReader(open(self.path, 'rb'))


if __name__ == '__main__':
    file = PrinterFile("/Users/andrewmoskalev/PycharmProjects/PrinterCore/ура программа коллоквиума.pdf")
    print(f'Информация о "{file.name}"')
    print(f'Страниц: {file.get_pages_count()}')

