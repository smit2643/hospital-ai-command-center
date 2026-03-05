from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

out_dir = Path('/app/sample_data')
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / 'hospital_dummy_lab_report.png'

img = Image.new('RGB', (1240, 1600), color='white')
draw = ImageDraw.Draw(img)

try:
    title_font = ImageFont.truetype('DejaVuSans.ttf', 44)
    head_font = ImageFont.truetype('DejaVuSans.ttf', 30)
    text_font = ImageFont.truetype('DejaVuSans.ttf', 24)
except OSError:
    title_font = head_font = text_font = ImageFont.load_default()

y = 50
draw.text((70, y), 'CITY CARE MULTISPECIALTY HOSPITAL', fill='black', font=title_font)
y += 70
draw.text((70, y), 'Pathology Department - Laboratory Report', fill='black', font=head_font)
y += 60

draw.text((70, y), 'Patient Name: Rohan Shah', fill='black', font=text_font)
y += 40
draw.text((70, y), 'Patient ID: CCMH-PT-2026-0091', fill='black', font=text_font)
y += 40
draw.text((70, y), 'Doctor Name: Dr. Aria Menon', fill='black', font=text_font)
y += 40
draw.text((70, y), 'Hospital Name: City Care Multispecialty Hospital', fill='black', font=text_font)
y += 40
draw.text((70, y), 'Report Date: 2026-03-05', fill='black', font=text_font)
y += 70

draw.text((70, y), 'Test Name                      Value      Unit      Reference Range', fill='black', font=text_font)
y += 35
draw.line((70, y, 1170, y), fill='black', width=2)
y += 20

rows = [
    'Hemoglobin                    13.5       g/dL      12.0-16.0',
    'WBC Count                     7800       /uL       4000-11000',
    'Platelet Count                2.7        lakh/uL   1.5-4.5',
    'Blood Glucose (Fasting)       94         mg/dL     70-100',
    'Creatinine                    0.9        mg/dL     0.6-1.2',
]

for row in rows:
    draw.text((70, y), row, fill='black', font=text_font)
    y += 42

y += 35
draw.text((70, y), 'Clinical Note: Mild iron deficiency trend. Continue diet plan and hydration.', fill='black', font=text_font)
y += 50
draw.text((70, y), 'Authorized Signatory: _____________________', fill='black', font=text_font)

img.save(out_file)
print(f'Generated: {out_file}')
