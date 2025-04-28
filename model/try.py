import os
import random
import subprocess
from music21 import stream, note, meter, clef, key, environment, layout, lily

# === Set up LilyPond path ===
us = environment.UserSettings()
us['lilypondPath'] = r'C:\Program Files\lilypond-2.24.4\bin\lilypond.exe'  # Adjust if needed

# === Output folder ===
output_folder = r"C:\Users\conta\Desktop\data"
os.makedirs(output_folder, exist_ok=True)

# === Notes and durations ===
notes = ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4']
durations = {'whole': 4.0, 'half': 2.0, 'quarter': 1.0}

# === Generate one bar ===
def generate_bar():
    bar = stream.Measure()
    total = 0.0
    while total < 4.0:
        remaining = 4.0 - total
        allowed = [d for d, val in durations.items() if val <= remaining]
        dur = random.choice(allowed)
        pitch = random.choice(notes)
        bar.append(note.Note(pitch, quarterLength=durations[dur]))
        total += durations[dur]
    return bar

# === Generate 50 sheets ===
for i in range(1, 51):
    score = stream.Score()
    part = stream.Part()
    part.append(clef.TrebleClef())
    part.append(meter.TimeSignature('4/4'))
    part.append(key.KeySignature(0))  # C Major

    for _ in range(4):  # 4 systems
        for _ in range(random.randint(4, 5)):  # 4–5 bars per line
            part.append(generate_bar())
        part.append(layout.SystemLayout(isNew=True))  # Line break

    score.append(part)

    # === Write to .ly file ===
    ly_path = os.path.join(output_folder, f'sheet_{i}.ly')
    score.write('lilypond', fp=ly_path)

    # === Clean broken LilyPond code ===
    with open(ly_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    cleaned_lines = []
    inside_layout = False
    for line in lines:
        if "\\layout" in line:
            inside_layout = True
            continue
        if inside_layout:
            if "}" in line:
                inside_layout = False
            continue
        if "RemoveEmptyStaffContext" in line:
            continue
        if "VerticalAxisGroup" in line:
            continue
        cleaned_lines.append(line)

    with open(ly_path, 'w', encoding='utf-8') as file:
        file.writelines(cleaned_lines)

    # === Render to PNG using LilyPond ===
    subprocess.run([
        us['lilypondPath'],
        '--png',
        '-dbackend=eps',
        '-dresolution=600',
        '-o', output_folder,
        ly_path
    ])

print("✅ All 50 sheet music PNGs saved to:", output_folder)
