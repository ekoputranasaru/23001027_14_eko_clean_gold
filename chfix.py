import re
from flask import Flask, jsonify
from flask import request
import flask
from flasgger import Swagger, LazyString,LazyJSONEncoder
from flasgger import swag_from
import pandas as pd
import os
from werkzeug.utils import secure_filename
import sqlite3


class CustomFlaskAppWithEncoder(Flask):
    json_provider_class = LazyJSONEncoder

app = CustomFlaskAppWithEncoder(__name__)

swagger_template = dict(
    info = {
        'title' : LazyString(lambda: "API Documentation for Data Processing and Modeling"),
        'version' : LazyString(lambda: "1.0.0"),
        'description' : LazyString(lambda: "Dokumentasi API untuk Data Processing dan Modeling"),
    },
    host = LazyString(lambda: request.host)
)

swagger_config={
    "headers":[],
    "specs":[
        {
            "endpoint":'docs',
            "route":'/docs.json',
        }
    ],
    "static_url_path":"/flasgger_static",
    "swagger_ui":True,
    "specs_route":"/docs/"
}

file_path = r'C:\Users\ekopu\binar-data-science\binar-data-science\docs'
data = pd.read_csv(file_path + '\data.csv', encoding='iso-8859-1')

#fungsi clean
def cleantext(text):
    cleaned_text = re.sub(r'https?://\S+|www\.\S+', '', text)
    cleaned_text = re.sub(r'[^a-zA-Z0-9\s]', '', cleaned_text)
    cleaned_text = re.sub(r'x[0-9a-fA-F]+', '', cleaned_text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text
data['Cleaned_Tweet'] = data['Tweet'].str.lower()
data['Cleaned_Tweet'] = data['Tweet'].apply(cleantext)


#menentukan lookasi folder dan jenis file
UPLOAD_FOLDER = 'docs'
ALLOWED_EXTENSIONS = {'csv'}

#cek lookasi folder dan namafile
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


swagger=Swagger(app, template=swagger_template, config=swagger_config)
#upload raw data
@app.route('/upload_csv', methods=['POST'])
@swag_from("docs/upload_csv.yml", methods = ['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada bagian file'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'Tidak ada file yang dipilih'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({'message': 'File berhasil diupload'}), 200
    else:
        return jsonify({'error': 'Jenis file tidak diizinkan (harus berupa file CSV)'}), 400



#coba
@swag_from("docs/clean.yml", methods=['POST'])
@app.route('/clean_data1', methods=['POST'])
def clean_data1():
    file = request.files['file']
    kolom = request.args.get('kolom')

    if not file:
        return jsonify({'error': 'Parameter "file" harus diisi'}), 400
    if not kolom:
        return jsonify({'error': 'Parameter "kolom" harus diisi'}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    if not os.path.isfile(file_path):
        return jsonify({'error': 'File tidak ditemukan'}), 404

    data_clean = pd.read_csv(file_path, encoding='iso-8859-1')

    if kolom not in data_clean.columns:
        return jsonify({'error': f'Kolom "{kolom}" tidak ditemukan dalam file CSV'}), 400

    cleaned_text = data_clean[kolom].apply(cleantext)
    cleaned_text = cleaned_text.str.lower()

    # Simpan data yang telah dibersihkan ke dalam database SQLite3
    conn = sqlite3.connect('data_clean.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cleaned_data (
            id INTEGER PRIMARY KEY,
            original_text TEXT,
            cleaned_text TEXT
        )
    ''')

    original_text = data_clean[kolom].tolist()
    original_text = [str(text) for text in original_text]

    for original, cleaned in zip(original_text, cleaned_text):
        cursor.execute('INSERT INTO cleaned_data (original_text, cleaned_text) VALUES (?, ?)', (original, cleaned))

    conn.commit()
    conn.close()

    return jsonify({'message': f'Data pada kolom "{kolom}" berhasil dibersihkan dan disimpan dalam database SQLite3'}), 200


@swag_from("docs/text_processing.yml", methods = ['POST'])
@app.route('/text_processing', methods=['POST'])
def textclean():

    text = request.form.get('text')
    cleaned_text = re.sub(r'[^a-zA-Z0-9]', ' ', text)

    # Menyimpan data ke dalam database
    conn = sqlite3.connect('data_clean.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS text (
            id INTEGER PRIMARY KEY,
            original_text TEXT,
            cleaned_text TEXT
        )
    ''')
    
    cursor.execute('''
        INSERT INTO text (original_text, cleaned_text)
        VALUES (?, ?)
    ''', (text, cleaned_text))
    conn.commit()

    json_response = {
        'status_code': 200,
        'description': "Original Teks",
        'data': cleaned_text,
    }

    response_data = jsonify(json_response)
    return response_data

#batas challenge
@swag_from("docs/hello_world.yml", methods = ['GET'])
@app.route('/', methods=['GET'])
def hello_world():
    json_response = {
        'status_code': 200,
        'description': "Menyapa Hello World",
        'data': "Hello World",
    }

    response_data = jsonify(json_response)
    return response_data

@swag_from("docs/hello_world.yml", methods = ['GET'])
@app.route('/text', methods=['GET'])
def text():
    json_response = {
        'status_code': 200,
        'description': "Original Teks",
        'data': "Halo, apa kabar semua?",
    }

    response_data = jsonify(json_response)
    return response_data
    
#coba clean da
@swag_from("docs/hello_world.yml", methods = ['GET'])
@app.route('/text-clean', methods=['GET'])
def text_clean():
    text = data['Cleaned_Tweet'].tolist()
    
    json_response = {
        'status_code': 200,
        'description': "Data Teks yang telah diolah",
        'data': text,
    }        
    response_data=jsonify(json_response)
    return response_data
if __name__ == '__main__':
    app.run()
