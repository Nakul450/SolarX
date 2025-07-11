from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import cv2
import torch
import numpy as np
from ultralytics import YOLO
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configure MySQL Database
##app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root@localhost/solar_detection'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root@localhost/solar_detection'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

UPLOAD_FOLDER = 'static/uploads'
RESULT_FOLDER = 'static/results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# Load YOLO model
MODEL_PATH = "models/best.pt"
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file {MODEL_PATH} not found!")

model = YOLO(MODEL_PATH)

# Database Model for Saving Images & Results
class DetectionResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    result_image = db.Column(db.String(255), nullable=False)
    solar_panel_count = db.Column(db.Integer, nullable=False)
    total_area = db.Column(db.Float, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, filename, result_image, solar_panel_count, total_area):
        self.filename = filename
        self.result_image = result_image
        self.solar_panel_count = solar_panel_count
        self.total_area = total_area

# Create Tables (Run Once)
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Secure filename
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Load and preprocess image
    image = cv2.imread(filepath)
    if image is None:
        return jsonify({'error': 'Invalid image format'}), 400

    # Process image with YOLO model
    results = model(filepath)

    # Extract bounding boxes
    detected_image = image.copy()
    total_area = 0
    solar_panel_count = 0

    for box in results[0].boxes.data.cpu().numpy():  # Extract bounding boxes safely
        x1, y1, x2, y2, confidence, class_id = map(int, box[:6])
        
        # Draw bounding box
        label = f"Solar Panel: {confidence:.2f}"
        cv2.rectangle(detected_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(detected_image, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Calculate area
        area = (x2 - x1) * (y2 - y1)
        total_area += area
        solar_panel_count += 1

    # Save processed image
    result_filename = f"detected_{filename}"
    result_image_path = os.path.join(RESULT_FOLDER, result_filename)
    cv2.imwrite(result_image_path, detected_image)

    # Save to Database
    detection_entry = DetectionResult(
        filename=filename,
        result_image=result_image_path,
        solar_panel_count=solar_panel_count,
        total_area=total_area
    )
    db.session.add(detection_entry)
    db.session.commit()

    return jsonify({
        'result_image': f'/static/results/{result_filename}',
        'solar_panel_count': solar_panel_count,
        'total_area': total_area
    })

@app.route('/static/results/<filename>')
def serve_result(filename):
    return send_from_directory(RESULT_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
