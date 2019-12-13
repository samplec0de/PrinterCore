import random
import string
import requests
import img2pdf
import tempfile

from PIL import Image
from PyPDF2 import PdfFileReader
from pathlib import Path


def random_string(length=10):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


class PrinterFileException(Exception):
    pass


class PrinterFile:
    pdf = None
    file_type = None
    file = None
    name = None
    path = None
    extension = None
    pdf_path = None
    temp_dir = None
    office_extensions = ['txt', 'rtf', 'fodt', 'doc', 'docx', 'odt', 'xls', 'xlsx', 'ods', 'ppt', 'pptx', 'odp']

    def __init__(self, path):
        self.path = path
        self.file = Path(path)
        self.temp_dir = tempfile.TemporaryDirectory()
        if not self.file.exists() or not self.file.is_file():
            raise PrinterFileException("File does not exist")
        self.name = self.file.name
        self.extension = self.name.split('.')[-1].lower()
        supported_extensions = ["pdf", "png", "jpg", "docx"]
        if self.extension not in supported_extensions:
            raise PrinterFileException(f"File extension {self.extension} is not supported")
        if self.extension == "pdf":
            self.file_type = 'pdf'
            self.pdf_path = path
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
            jpg_path = f'{self.temp_dir.name}/{random_string()}.jpg'
            self.pdf_path = f'{self.temp_dir.name}/{random_string()}.pdf'
            background.save(jpg_path, 'JPEG', quality=80)
            with open(self.pdf_path, "wb") as f:
                f.write(img2pdf.convert(f'{jpg_path}', layout_fun=layout_fun))
            self.load_pdf(self.pdf_path)
        elif self.extension == 'jpg':
            self.file_type = 'jpg'
            self.pdf_path = f'{self.temp_dir.name}/{random_string()}.pdf'
            # specify paper size (A4)
            a4inpt = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))
            layout_fun = img2pdf.get_layout_fun(a4inpt)
            with open(self.pdf_path, "wb") as f:
                f.write(img2pdf.convert(f'{self.path}', layout_fun=layout_fun))
            self.load_pdf(self.pdf_path)
        elif self.extension in self.office_extensions:
            self.file_type = self.extension
            url = f'http://10.7.0.100:3000/convert/office'
            r = requests.post(url, files={'input.docx': open(self.path, 'rb')})
            if r.status_code != 200:
                raise PrinterFileException(f"Conversion error. HTTP code {r.status_code}")
            self.pdf_path = f'{self.temp_dir.name}/{random_string()}.pdf'
            with open(self.pdf_path, 'wb') as binary_file:
                binary_file.write(r.content)
            self.load_pdf(self.pdf_path)

    def get_pages_count(self):
        # if self.file_type in ['pdf', 'png']:
        return self.pdf.getNumPages()

    def load_pdf(self, custom_path=None):
        if custom_path is None:
            self.pdf = PdfFileReader(open(self.path, 'rb'))
        else:
            self.pdf = PdfFileReader(open(custom_path, 'rb'))

    def save(self, save_to):
        # if self.extension in ['pdf', 'png', 'jpg']:
        with open(self.pdf_path, 'rb') as src:
            with open(save_to, 'wb') as out:
                out.write(src.read())


if __name__ == '__main__':
    save_to = '/Users/andrewmoskalev/PycharmProjects/PrinterCore/result.pdf'
    # file = PrinterFile("/Users/andrewmoskalev/Downloads/Копия Go plakat.pdf")
    # file = PrinterFile("/Users/andrewmoskalev/PycharmProjects/PrinterCore/Снимок экрана 2019-12-10 в 23.36.57.png")
    # file = PrinterFile("/Users/andrewmoskalev/PycharmProjects/PrinterCore/IMG_4666.JPG")
    file = PrinterFile("/Users/andrewmoskalev/Desktop/Информатика. Переводной экзамен. Теория.docx")
    print(f'Информация о "{file.name}"')
    print(f'Тип файла: {file.file_type}')
    print(f'Страниц: {file.get_pages_count()}')
    file.save(save_to)
    print(f'pdf-файл сохранён в {save_to}')
