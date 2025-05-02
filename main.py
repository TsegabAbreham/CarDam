# app.py (updated)
from flask import Flask, render_template, request, send_file
from inference_sdk import InferenceHTTPClient
from PIL import Image, ImageDraw
from bs4 import BeautifulSoup
import requests, os, uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="4qcbtf9iBt4zBqf5P8PU"
)

# Color mapping for each damage class (unchanged)
CLASS_COLORS = {
    'Front-Windscreen-Damage': ('Blue', '#3498db'),
    # ... (other mappings) ...
}
default_color = ('Red', '#e74c3c')


def get_price_estimate(make, model, year, damage_class):
    """
    Scrape RepairPal (or similar) for estimated repair cost range.
    Returns a string like "$100 - $300" or 'N/A' on failure.
    """
    # Create URL slug for damage component
    slug = damage_class.lower().replace(' ', '-')
    # Example RepairPal estimator URL pattern
    url = f"https://www.repairpal.com/estimator/{make}/{model}/{year}/{slug}"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Inspect RepairPal page to find the cost range element
        elem = soup.find('span', class_='estimator-range') or soup.find('div', class_='cost-range')
        if elem:
            return elem.get_text(strip=True)
    except Exception as e:
        print(f"Estimate lookup failed for {damage_class}: {e}")
    return 'N/A'

@app.route('/', methods=['GET', 'POST'])
def index():
    result = False
    result_text = ''
    filename = None
    detected = []

    if request.method == 'POST':
        # Capture car info from form
        make = request.form.get('make', '').strip()
        model = request.form.get('model', '').strip()
        year = request.form.get('year', '').strip()

        # Save uploaded image
        image_file = request.files['image']
        filename = f"{uuid.uuid4().hex}.jpg"
        path = os.path.join(UPLOAD_FOLDER, filename)
        image_file.save(path)

        try:
            # Run inference
            response = CLIENT.infer(path, model_id="cardamage-l4vtd/1")
            img = Image.open(path).convert("RGB")
            draw = ImageDraw.Draw(img)
            preds = response.get('predictions', [])

            for p in preds:
                cls = p.get('class', '')
                name, hex_color = CLASS_COLORS.get(cls, default_color)
                # Draw bounding box
                x0 = p['x'] - p['width']/2
                y0 = p['y'] - p['height']/2
                x1 = x0 + p['width']
                y1 = y0 + p['height']
                draw.rectangle([x0, y0, x1, y1], outline=hex_color, width=4)

                # Get price estimate
                estimate = get_price_estimate(make, model, year, cls)
                detected.append({
                    'class': cls,
                    'color_name': name,
                    'color_hex': hex_color,
                    'estimate': estimate
                })

            # Save annotated image
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
