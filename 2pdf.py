import argparse

from printer_utils import PrinterFile

parser = argparse.ArgumentParser(description='Конвертер популярных офисных форматов в pdf')
parser.add_argument('source_file', metavar='SOURCE_FILE', type=str, nargs=1,
                    help='полный путь до исходного файла')
parser.add_argument('output_file', metavar='OUTPUT_FILE', type=str, nargs=1,
                    help='полный путь до файла, в который необходимо сохранить результат (.pdf)')
parser.add_argument('server', metavar='HANDLER', type=str, nargs='?', default='http://10.7.0.100:3000/convert/office',
                    help='адрес веб-обработчика (по умолчанию: http://10.7.0.100:3000/convert/office)')
args = parser.parse_args()
vars = {'server': args.server, 'source_file': args.source_file[0], 'output_file': args.output_file[0]}
file = PrinterFile(path=vars['source_file'], url=vars['server'])
print(file.get_pages_count())
file.save(vars['output_file'])
