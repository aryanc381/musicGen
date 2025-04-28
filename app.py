from flask import Flask, render_template, request, redirect, flash, url_for
import os
import pickle
import shutil
import tempfile
import cv2
import numpy as np
from music21 import stream, note, chord, clef, midi, metadata
from tensorflow.keras.models import load_model
from ultralytics import YOLO
from werkzeug.utils import secure_filename

# === App setup ===
app = Flask(__name__)
app.secret_key = "AIzaSyA1KSj9kxCszjq_1KE4V099WcMXUhUsgWw"

UPLOAD_FOLDER = "static/uploads"
DOWNLOAD_FOLDER = "static/downloads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["DOWNLOAD_FOLDER"] = DOWNLOAD_FOLDER

# === Load Models ===
model_path = "model/advanced_melody_to_chord_model.h5"
note_encoder_path = "model/note_encoder.pkl"
chord_encoder_path = "model/chord_encoder.pkl"
yolo_model_path = "model/best.pt"

model = load_model(model_path)
yolo = YOLO(yolo_model_path)

with open(note_encoder_path, "rb") as f:
    note_encoder = pickle.load(f)
with open(chord_encoder_path, "rb") as f:
    chord_encoder = pickle.load(f)

# === Utility Functions ===
def split_and_detect(image_path, annotated_save_path=None):
    results = yolo.predict(source=image_path, conf=0.25, iou=0.45, save=False)[0]

    if annotated_save_path:
        annotated_img = results.plot()
        cv2.imwrite(annotated_save_path, annotated_img)

    boxes = results.boxes.xyxy.cpu().numpy()
    class_ids = results.boxes.cls.cpu().numpy()
    labels = [yolo.names[int(cls_id)] for cls_id in class_ids]
    detections = list(zip(boxes, labels))

    H = cv2.imread(image_path).shape[0]
    clef_centers = [(y1 + y2) / 2 for (x1, y1, x2, y2), lbl in detections if lbl == "Treble Clef"]
    if not clef_centers:
        return []

    clef_centers.sort()
    boundaries = [0] + [(clef_centers[i] + clef_centers[i + 1]) / 2 for i in range(len(clef_centers) - 1)] + [H]
    all_measures = []

    for m in range(len(boundaries) - 1):
        top = boundaries[m]
        bottom = boundaries[m + 1]
        events = []
        for (x1, y1, x2, y2), lbl in detections:
            if lbl == "Treble Clef":
                continue
            yc = (y1 + y2) / 2
            if top <= yc < bottom:
                events.append((int(x1), lbl))
        events.sort(key=lambda e: e[0])
        all_measures.append([lbl for _, lbl in events])

    return all_measures

def group_notes(measures):
    grouped_all = []
    for seq in measures:
        groups = []
        current = []
        for label in seq:
            if label == "bar":
                if current:
                    groups.append(current)
                    current = []
            else:
                current.append(label)
        if current:
            groups.append(current)
        grouped_all.append(groups)
    return grouped_all

def generate_midi_from_groups(grouped):
    melody_chunks = []
    for measure in grouped:
        for group in measure:
            notes = group.copy()
            if len(notes) < 4:
                notes += [notes[-1]] * (4 - len(notes))
            elif len(notes) > 4:
                notes = notes[:4]
            melody_chunks.append(notes)

    predicted_chords = []
    for chunk in melody_chunks:
        try:
            encoded = note_encoder.transform(chunk).reshape(1, -1)
            pred = model.predict(encoded)
            class_index = np.argmax(pred)
            chord_label = chord_encoder.inverse_transform([class_index])[0]
        except Exception:
            chord_label = "C Major (C E G)"
        predicted_chords.append(chord_label)

    score = stream.Score()
    score.metadata = metadata.Metadata()
    score.metadata.title = "AI Generated MIDI"
    score.metadata.composer = "Aryan and Abdul"

    melody_part = stream.Part()
    melody_part.append(clef.TrebleClef())
    for chunk in melody_chunks:
        for pitch in chunk:
            melody_part.append(note.Note(pitch, quarterLength=1.0))

    bass_part = stream.Part()
    bass_part.append(clef.BassClef())
    for chord_str in predicted_chords:
        notes = chord_str.split("(")[-1].replace(")", "").split()
        c_notes = [note.Note(n) for n in notes]
        for n in c_notes:
            n.octave = 3
        c = chord.Chord(c_notes)
        c.quarterLength = 4.0
        bass_part.append(c)

    score.insert(0, melody_part)
    score.insert(0, bass_part)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp:
        mf = midi.translate.streamToMidiFile(score)
        mf.open(tmp.name, 'wb')
        mf.write()
        mf.close()
        return tmp.name, predicted_chords

# === Routes ===
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/project", methods=["GET", "POST"])
def project():
    if request.method == "POST":
        if 'image' not in request.files:
            flash("No image file uploaded!", "danger")
            return redirect(request.url)

        file = request.files["image"]
        if file.filename == "":
            flash("No file selected!", "warning")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(image_path)

        annotated_image_path = os.path.join(app.config["DOWNLOAD_FOLDER"], "annotated_prediction.jpg")
        measures = split_and_detect(image_path, annotated_save_path=annotated_image_path)

        if not measures:
            flash("No treble clefs or notes detected.", "danger")
            return redirect(request.url)

        grouped = group_notes(measures)
        midi_path, predicted_chords = generate_midi_from_groups(grouped)

        final_midi_path = os.path.join(app.config["DOWNLOAD_FOLDER"], "melody.mid")
        shutil.copy(midi_path, final_midi_path)

        return render_template("project.html", chords=", ".join(predicted_chords))

    return render_template("project.html")

@app.route("/development")
def development():
    return render_template("development.html")

# === Run App ===
if __name__ == "__main__":
    app.run(debug=True)
