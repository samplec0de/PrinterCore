import hashlib
import json
import logging
import traceback
import mysql.connector.pooling
from pathlib import Path
from flask import Flask, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from printer_utils import PrinterFile, random_string, PrinterFileException

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'txt', 'rtf', 'fodt', 'doc',
                      'docx', 'odt', 'xls', 'xlsx', 'ods', 'ppt', 'pptx', 'odp'}

app = Flask(__name__)
app.secret_key = open('/Users/andrewmoskalev/PycharmProjects/PrinterCore/secret', 'r').read()
app.config['SESSION_TYPE'] = 'filesystem'
app.config['ROOT'] = f'{Path(app.instance_path).parent}'
app.config['UPLOAD_FOLDER'] = f'{app.config["ROOT"]}/files'
app.config['READY_FOLDER'] = f'{app.config["ROOT"]}/ready_files'
logging.basicConfig(filename=f'{app.config["ROOT"]}/myapp.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger(__name__)
db_config = json.loads(open(f'{app.config["ROOT"]}/mysql.json', 'r').read())
cnx_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="printer", pool_size=1, **db_config)


def _iter_row(cursor):
    while True:
        rows = cursor.fetchmany(48)
        if not rows:
            break
        for row in rows:
            yield row


def stringify(array):
    for i in range(len(array)):
        if type(array[i]) != str:
            array[i] = str(array[i])
    return array


def allowed_file(filename):
    return '.' in filename and filename.split('.')[-1].lower() in ALLOWED_EXTENSIONS


def md5(filename):
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            logger.info("POST запрос на /, нет файла")
            return jsonify({'error': 'No file'})
        file = request.files['file']
        if file.filename == '':
            logger.info("POST запрос на /, имя файла пустое")
            return jsonify({'error': 'No selected file'})
        if file and allowed_file(file.filename):
            local_filename = secure_filename(file.filename)
            if len(local_filename) > 250:
                logger.info("POST запрос на /, слишком длинное имя файла")
                return jsonify({'error': 'Filename too long (limit 250)'})
            logger.info("POST запрос на /")
            cnx = cnx_pool.get_connection()
            cursor = cnx.cursor(buffered=True)
            try:
                cursor.execute('SET NAMES utf8mb4')
                cnx.commit()
                local_file = f"{Path(app.config['UPLOAD_FOLDER']) / local_filename}"
                file.save(local_file)
                src_md5 = md5(local_file)
                cursor.execute("INSERT INTO `imports` (`filename`, `local_filename`, `src_md5`)"
                               " values (%s, %s, %s)",
                               [file.filename, local_filename, src_md5])
                cursor.execute("SELECT LAST_INSERT_ID()")
                cnx.commit()
                import_id = cursor.fetchone()[0]
                logger.info(f"Конвертация файла {file.filename}")
                pf = PrinterFile(local_file)
                pages = pf.get_pages_count()
                result_filename = f'{random_string()}.pdf'
                result_file = f"{Path(app.config['READY_FOLDER']) / result_filename}"
                pf.save(result_file)
                logger.info(f"Конвертация файла {file.filename} завершена успешно")
                cursor.execute("UPDATE `imports` SET result_file=%s, pages=%s WHERE import_id=%s",
                               [result_filename, str(pages), str(import_id)])
                cnx.commit()
                cursor.close()
                cnx.close()
                return jsonify(
                    {
                        'import_id': import_id,
                        'source_md5': f'{src_md5}',
                        'pages_count': pages
                    }
                )
            except PrinterFileException as pfe:
                cursor.close()
                cnx.close()
                logger.error(f"Ошибка конвертации файла (PrinterFileException)"
                             f" {file.filename}: {traceback.format_exc()}")
                return jsonify({'error': f'{pfe}'})
            except Exception as e:
                cursor.close()
                cnx.close()
                logger.error(f"Ошибка конвертации файла {file.filename}: {traceback.format_exc()}")
                return jsonify({'error': f'{e}'})
        logger.info(f"POST запрос на /, но имя файла не прошло проверку {file.filename}")
        return jsonify({'error': 'Bad filename'})
    logger.info("GET запрос на /")
    return '''
    <!doctype html>
    <title>Загрузка файла</title>
    <h1>Загрузка нового файла</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''


@app.route('/imports/<import_id>')
def imports(import_id):
    logger.info(f"Запрос импорта {import_id}")
    cnx = cnx_pool.get_connection()
    cursor = cnx.cursor(buffered=True, dictionary=True)
    not_found = jsonify({"error": "Import does not exist"})
    deleted = jsonify({"error": "Import removed from server"})
    try:
        cursor.execute("SELECT COUNT(*) FROM `imports` WHERE import_id=%s", [str(import_id)])
        cnx.commit()
        if cursor.fetchone()['COUNT(*)'] == 0:
            cursor.close()
            cnx.close()
            logger.info(f"Запрос импорта {import_id}: не найден")
            return not_found
        cursor.execute("SELECT * FROM `imports` WHERE import_id=%s", [str(import_id)])
        cnx.commit()
        result = cursor.fetchone()
        if result['exists'] == 0:
            cursor.close()
            cnx.close()
            logger.info(f"Запрос импорта {import_id}: удален")
            return deleted, 404
        cursor.close()
        cnx.close()
        logger.info(f"Импорт {import_id}: {result['result_file']} ({result['pages']})")
        return jsonify({"filename": result['result_file'], "pages": result['pages']}), 200
    except Exception as e:
        cursor.close()
        cnx.close()
        logger.error(f"Ошибка обработки import {import_id}: {traceback.format_exc()}")
        return jsonify({"error": f"{e}"}), 400


@app.route('/files/<filename>')
def files(filename):
    logger.info(f"Запрос файла {filename}")
    file = Path(app.config['READY_FOLDER']) / filename
    if not file.exists():
        logger.info(f"Запрос файла {filename}: ошибка, файл не найден")
        return jsonify({"error": "File does not exist"})
    logger.info(f"Запрос файла {filename}: отдаю файл")
    return send_from_directory(app.config['READY_FOLDER'], filename)


@app.route('/hash/<file_md5>')
def by_hash(file_md5):
    logger.info(f"Запрос файла по md5 {file_md5}")
    cnx = cnx_pool.get_connection()
    cursor = cnx.cursor(buffered=True, dictionary=True)
    not_found = jsonify({"error": "Import does not exist"})
    deleted = jsonify({"error": "Import removed from server"})
    try:
        cursor.execute("SELECT COUNT(*) FROM `imports` WHERE src_md5=%s", [file_md5])
        cnx.commit()
        if cursor.fetchone()['COUNT(*)'] == 0:
            cursor.close()
            cnx.close()
            logger.info(f"Запрос файла по md5 {file_md5}: файл не найден")
            return not_found, 404
        cursor.execute("SELECT * FROM `imports` WHERE src_md5=%s", [file_md5])
        cnx.commit()
        res = cursor.fetchone()
        if res['exists'] == 0:
            logger.info(f"Запрос файла по md5 {file_md5}: файл удален")
            cursor.close()
            cnx.close()
            return deleted, 404
        cursor.close()
        cnx.close()
        logger.info(f"Импорт md5 {file_md5}: {res['result_file']} ({res['pages']})")
        return jsonify({"filename": res['result_file'], "pages": res['pages']}), 200
    except Exception as e:
        logger.error(f"Ошибка обработки import md5 {file_md5}: {traceback.format_exc()}")
        cursor.close()
        cnx.close()
        return jsonify({"error": f"{e}"}), 400
    cursor.close()
    cnx.close()
    logger.error(f"Ошибка обработки unknown import md5 {file_md5}: {traceback.format_exc()}")
    return jsonify({"error": "unknown"}), 400


if __name__ == '__main__':
    app.run()
