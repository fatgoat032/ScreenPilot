
import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import subprocess
import json
import imagehash
import time
import requests
import websocket
from PIL import Image, ImageDraw, ImageFont
import logging
logging.disable(logging.DEBUG)
logging.disable(logging.WARNING)
from paddleocr import PaddleOCR 

os.environ.pop("GTK_PATH", None) #apps installed via Snap override the system's GTK_PATH with their own path, and as the screenshot's subprocess inherits the parent's environment, it will go to the app's gtk_path instead of the system's and crashes, by popping this GTK_PATH, it will default to the system's.

class ScreenParser:
    def __init__(self):
        print("loading OCR model, this may take a few seconds")
        self.reader = PaddleOCR(lang='en', use_gpu=False, use_angle_cls=False, ocr_version='PP-OCRv4', enable_mkldnn=False, cpu_threads=4)#made angle_cls false as i think use_angle_cls isn't efficient, not worth adding this much overhead when majority of text will be horizontal
        print("OCR loaded")
    
    def capture(self, path="/tmp/screenpilot_screenshot.png"):
        time.sleep(2.0)
        subprocess.run(['gnome-screenshot', '-f', path], check=True)
        return path
    
    def parse(self, image_path):
        results = self.reader.ocr(image_path)
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        elements = []
        for i, line in enumerate(results[0]):
            bbox = line[0]
            text = line[1][0] 
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
    
class BrowserParser:
    def __init__(self):
        self.webskt = None
        self.id = 0

    def connect(self, domain=None):
        for i in range(5):
            try:
                response = requests.get("http://localhost:9000/json")
                tabs = response.json()
                break
            except:
                pass
            time.sleep(1.0) #giving time for connection to be established
          
        if domain:
            tab = next(t for t in tabs if domain in t.get('url', ''))
        else:
            for i in range(len(tabs)):
                if tabs[i].get('type') == "page":
                    tab = tabs[i]
                    break
        self.webskt = websocket.create_connection(tab["webSocketDebuggerUrl"])
    
    def nextID(self):
        self.id += 1
        return self.id
    
    def parse_v2(self, expression):
        #for generic use, works with anything
        command = {"id": self.nextID(), "method": "Runtime.evaluate", "params": {"expression": expression}}
        self.webskt.send(json.dumps(command))
        response = json.loads(self.webskt.recv())
        print(f"recieved response:\n {response}\n")
        return response['result']['result'].get('value')
    def parse_v3(self, expression):
        #works only for DOM-dump expression, calles parse_v2, and then unwraps the extra layer
        response = json.loads(self.parse_v2(expression))
        return response
    
    def create_list(self):
        elements = []
        expression = """
        JSON.stringify([
            ...[...document.querySelectorAll('button, input, a')].filter(e => {
                const rect = e.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0 && rect.top >= 0 && rect.bottom <= window.innerHeight;
            }).map(e => {
                let text = (e.innerText || e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.getAttribute('title') || e.getAttribute('name') || e.getAttribute('id') || (e.tagName === 'INPUT' ? e.value : '') || '').trim();
                let type = e.type || '';
                let href = e.getAttribute('href') || '';
                let formaction = e.closest('form') ? e.closest('form').getAttribute('action') : '';
                return { tag: e.tagName, text: text, type: type, href: href, formaction: formaction };
            }).filter(e => e.type !== 'hidden' && e.text !== ''),
            ...[...document.querySelectorAll('form[action]')].map(f => ({
                tag: 'FORM',
                text: [...f.querySelectorAll('button')].map(b => b.textContent.trim()).join(' / '),
                type: '', 
                href: '', 
                formaction: f.getAttribute('action')
            })).filter(f => f.text !== '')
        ])
        """
        list = self.parse_v3(expression)
        for i, element in enumerate(list):
            if element['tag'] == "INPUT":
                selector = f'input[type="{element["type"]}"]'
                navigate_url = None
            elif element['tag'] == "BUTTON":
                selector = f'[...document.querySelectorAll("button")].find(b => b.innerText.includes("{element["text"]}"))'
                navigate_url = element.get('formaction') or None
            elif element['tag'] == "A":
                selector = f'a[href="{element["href"]}"]'
                navigate_url = element['href'] 
            elif element['tag'] == "FORM":
                navigate_url = element['formaction']
                selector = None
            new_element = {
                'id': i, 'text': element['text'], 'selector': selector, 'navigate_url': navigate_url
            }
            elements.append(new_element)
        return elements[:50]
    
    def send_key(self, key):
        for event_type in ['keyDown', 'keyUp']:
            self.webskt.send(json.dumps({"id": self.nextID(), "method": "Input.dispatchKeyEvent", "params": {"type": event_type, "key": key}}))
            self.webskt.recv()
            time.sleep(0.05)

            
    def execute(self, elements, action, url=None, id=None, text=None, key=None):
        if id is not None:
             print("id is belowwwww")
             print(id)
             selector = elements[id]['selector']
             print(selector)
             if action.lower() == "click":
                 if selector.startswith("[..."): #asking if its alr javascript
                     
                     expression = f"{selector}.click()"
                 else:
                     expression = f"document.querySelector('{selector}').click()"
             elif action.lower() == "value":
                 if selector.startswith("[..."):
                     js = """
                     (function() {
                         let element = (selector_here);
                         element.value = 'text_here';
                         element.dispatchEvent(new Event('input', { bubbles: true }))); 
                         element.dispatchEvent(new Event('change', { bubbles: true })))
                         return element.value;
                     })()
                     """ #modern web frameworks don't watch for the screen but for physical user input, we trick the framework into thinking a real human typed by firing these two events.
                     #input fires on every keystroke while change is for when the user stops typing, standard is input but some older frameworks need both.
                     #bubbles: true makes sure the event travels up the html tree, to be sure it dosn't go unnoticed
                     expression = js.replace("selector_here", selector).replace("text_here", text) #did this as i got a lot of syntax errors when i tried to do it manually
                 else:
                     js = """
                     (function() {
                         let element = document.querySelector('selector_here');
                         element.value = 'text_here';
                         element.dispatchEvent(new Event('input', { bubbles: true }));
                         element.dispatchEvent(new Event('change', { bubbles: true }));
                         return element.value;
                     })()
                     """
                     expression = js.replace("selector_here", selector).replace("text_here", text)
             self.parse_v2(expression)
        else:
           if action.lower() == "key":
             self.send_key(key)  
           elif action.lower() =="wait":
                time.sleep(2.0)  
           elif action.lower() == "navigate":
                command = {"id": self.nextID(), "method": "Page.navigate", "params": {"url": url}}
                self.webskt.send(json.dumps(command))
                self.webskt.recv()
                time.sleep(2.0)
           

    def get_title(self):
        return self.parse_v2("document.title")
    
    def get_url(self):
        return self.parse_v2("window.location.href")


                
        
    
        
    