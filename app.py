from flask import Flask, render_template, request,send_from_directory
import cv2
import pytesseract
import os
from datetime import datetime
import psycopg2

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# PostgreSQL config
DB_HOST = "localhost"
DB_NAME = "number_plate_db"
DB_USER = "postgresql"
DB_PASS = "password"

# Set Tesseract path if on Windows
pytesseract.pytesseract.tesseract_cmd = r'D:\software\Program Files (x86)\tesseract.exe'

def log_to_db(plate_text, image_name):
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO plate_logs (plate_text, image_name) VALUES (%s, %s)",
            (plate_text, image_name)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Database error:", e)

def extract_number_plate(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_russian_plate_number.xml")
    plates = plate_cascade.detectMultiScale(gray, 1.1, 4)

    plate_text = "No plate detected"
    for (x, y, w, h) in plates:
        roi = image[y:y+h, x:x+w]
        plate_text = pytesseract.image_to_string(roi, config='--psm 8')
        break

    return plate_text.strip()

# Serve images from the uploads folder
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['image']
        if file:
            filename = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + file.filename
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)

            plate_number = extract_number_plate(path)

            # Log to database
            log_to_db(plate_number, filename)

            return render_template('result.html', plate=plate_number, image=filename)

    return render_template('index.html')

@app.route('/admin')
def admin():
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cursor = conn.cursor()
        cursor.execute("SELECT plate_text, image_name, timestamp FROM plate_logs ORDER BY timestamp DESC")
        logs = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('admin.html', logs=logs)
    except Exception as e:
        return f"Database error: {e}"


if __name__ == '__main__':
    app.run(debug=True)
