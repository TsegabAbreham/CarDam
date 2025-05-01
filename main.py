from flask import Flask, render_template, request, send_file
from inference_sdk import InferenceHTTPClient
from PIL import Image, ImageDraw
import os, uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="4qcbtf9iBt4zBqf5P8PU"
)

# Color mapping for each damage class
CLASS_COLORS = {
    'Front-Windscreen-Damage': ('Blue', '#3498db'),
    'Headlight-Damage':         ('Green', '#27ae60'),
    'Rear-windscreen-Damage':   ('Orange', '#e67e22'),
    'RunningBoard-Dent':        ('Purple', '#9b59b6'),
    'Sidemirror-Damage':        ('Teal', '#1abc9c'),
    'Signlight-Damage':         ('Maroon', '#c0392b'),
    'Taillight-Damage':         ('Navy', '#2c3e50'),
    'bonnet-dent':              ('Olive', '#808000'),
    'doorouter-dent':           ('Brown', '#8b4513'),
    'fender-dent':              ('Coral', '#ff7f50'),
    'front-bumper-dent':        ('Crimson', '#dc143c'),
    'medium-Bodypanel-Dent':    ('DarkGreen', '#006400'),
    'pillar-dent':              ('DarkOrange', '#ff8c00'),
    'quaterpanel-dent':         ('DarkBlue', '#00008b'),
    'rear-bumper-dent':         ('DarkRed', '#8b0000'),
    'roof-dent':                ('DarkMagenta', '#8b008b')
}
default_color = ('Red', '#e74c3c')

@app.route('/', methods=['GET', 'POST'])
def index():
    result = False
    result_text = ''
    filename = None
    detected = []

    if request.method == 'POST':
        image_file = request.files['image']
        filename = f"{uuid.uuid4().hex}.jpg"
        path = os.path.join(UPLOAD_FOLDER, filename)
        image_file.save(path)

        try:
            response = CLIENT.infer(path, model_id="cardamage-l4vtd/1")
            img = Image.open(path).convert("RGB")
            draw = ImageDraw.Draw(img)
            preds = response.get('predictions', [])

            for p in preds:
                cls = p.get('class', '')
                name, hex_color = CLASS_COLORS.get(cls, default_color)
                x0 = p['x'] - p['width']/2
                y0 = p['y'] - p['height']/2
                x1 = x0 + p['width']
                y1 = y0 + p['height']
                draw.rectangle([x0, y0, x1, y1], outline=hex_color, width=4)
                detected.append({'class': cls, 'color_name': name, 'color_hex': hex_color})

            img.save(path)
            result = True
            result_text = f"{len(detected)} damage area(s) detected" if detected else "No damage detected."
        except Exception as e:
            result = True
            result_text = f"Error: {e}"

    return render_template(
        'index.html',
        result=result,
        result_text=result_text,
        filename=filename,
        detected=detected
    )

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)