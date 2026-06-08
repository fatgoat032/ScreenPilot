
import subprocess
import json
from PIL import Image, ImageDraw, ImageFont
import easyocr
import os
import time
os.environ.pop("GTK_PATH", None)

class ScreenParser:
    def __init__(self):
        print("loading OCR model, this may take a few seconds")
        self.reader = easyocr.Reader(['en'], gpu=False)
        print("OCR loaded")
    
    def capture(self, path="/tmp/screenpilot_screenshot.png"):
        time.sleep(2.0)
        subprocess.run(['gnome-screenshot', '-f', path], check=True)
        return path
    
    def parse(self, image_path):
        results = self.reader.readtext(image_path)
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        elements = []
        for i, (bbox, text, confidence) in enumerate(results):
            xs = [point[0] for point in bbox]
            ys = [point[1] for point in bbox]   
            center_xs = sum(xs) / 4
            center_ys = sum(ys) / 4
            elements.append({"id": i, "text": text, "center": (int(center_xs), int(center_ys))})
            draw.rectangle([min(xs), min(ys), max(xs), max(ys)], outline="red", width=2)
            draw.text((min(xs), min(ys)-10), str(i), fill="red")
        return image, elements
    
    def get_element_center(self, elements, element_id):
        for el in elements:
            if el["id"] == element_id:
                return el["center"]
        return None