import os

from PIL import Image
from PyPDF2 import PdfFileReader
from pathlib import Path
import img2pdf

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
        supported_extensions = ["pdf", "png"]
        if self.extension not in supported_extensions:
            raise PrinterFileException("File extension is not supported")
        if self.extension == "pdf":
            self.file_type = 'pdf'
            self.load_pdf()
            if self.pdf.isEncrypted:
                raise PrinterFileException("Encrypted pdf`s are not supported")
        elif self.extension == 'png':
            self.file_type = 'png'
            # specify paper size (A4)
            a4inpt = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))
            layout_fun = img2pdf.get_layout_fun(a4inpt)
            png = Image.open(self.path)
            png.load()
            background = Image.new("RGB", png.size, (255, 255, 255))
            background.paste(png, mask=png.split()[3])  # 3 is the alpha channel
            jpg_path = self.file.parent / 'tempfile.jpg'
            pdf_path = self.file.parent / 'tempfile.pdf'
            background.save(jpg_path, 'JPEG', quality=80)
            with open(pdf_path, "wb") as f:
                f.write(img2pdf.convert(f'{jpg_path}', layout_fun=layout_fun))
            os.remove(jpg_path)
            self.load_pdf(pdf_path)
            os.remove(pdf_path)
        elif self.extension == 'jpg':
            self.file_type = 'jpg'
            pdf_path = self.file.parent / 'tempfile.pdf'
            # specify paper size (A4)
            a4inpt = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))
            layout_fun = img2pdf.get_layout_fun(a4inpt)
            with open(pdf_path, "wb") as f:
                f.write(img2pdf.convert(f'{self.path}', layout_fun=layout_fun))
            self.load_pdf(pdf_path)
            os.remove(pdf_path)

    def get_pages_count(self):
        if self.file_type in ['pdf', 'png']:
            return self.pdf.getNumPages()

    def load_pdf(self, custom_path=None):
        if custom_path is None:
            self.pdf = PdfFileReader(open(self.path, 'rb'))
        else:
            self.pdf = PdfFileReader(open(custom_path, 'rb'))


if __name__ == '__main__':
    # file = PrinterFile("/Users/andrewmoskalev/Downloads/Копия Go plakat.pdf")
    file = PrinterFile("/Users/andrewmoskalev/PycharmProjects/PrinterCore/Снимок экрана 2019-12-10 в 23.36.57.png")

    print(f'Информация о "{file.name}"')
    print(f'Тип файла: {file.file_type}')
    print(f'Страниц: {file.get_pages_count()}')
    print('')
