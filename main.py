
from hand import WaylandPortalHand
from screen import ScreenParser, BrowserParser
from brain import PilotBrain
import subprocess
import os
from groq import Groq
import time
import imagehash
import asyncio
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('api_key') 
client = Groq(api_key=api_key)
def execute(data, hand, parser,  elements):
    action = data['action']
    if action == "left" or action == "right":
        id = data['id']
        x, y = parser.get_element_center(elements, id)
        hand.move_to(x, y)
        time.sleep(0.2)
        hand.click(action)
    elif action == "type":
        text = data['text']
        hand.type_text(text)
    elif action =="key":
        key = data['key']
        hand.key(key)
    elif action == "done":
        return True
    else:
        print("Unknown Action")
    return False


def launch_browser(browser):
    #first kill browser session if alr active
    subprocess.run(['pkill', '-f', browser], capture_output=True)
    for i in range(5):
        try:
          result = subprocess.run(['pgrep', '-f', 'remote-debugging-port=9000'], capture_output=True)  # so that pgrep dosn't print to terminal. pgrep searches for running process in port 9000, if nothing found returns 1
        except:
          time.sleep(2)
    time.sleep(1)
    subprocess.Popen([browser, '--remote-debugging-port=9000','--remote-allow-origins=*' ,f'--user-data-dir=/tmp/{browser}/debug']) #Popen so that process dosn't crash script until program closes
    time.sleep(2) #time for browser to open
if __name__ == "__main__":
    hand = WaylandPortalHand()
    parser = ScreenParser()
    AI = PilotBrain()
    webskt = BrowserParser()

    if not hand.create_session():
        print("CreateSession failed")
        exit()
    if not hand.select_devices():
        print("SelectDevices failed")
        exit()
    if not hand.select_sources():
        print("SelectSources Failed")
        exit()
    if not hand.start():
        print("Start has failed, try again")
        exit()
#main
#initializations
done = False
browsers = ["firefox", "chrome", "brave", "edge", "chromium", "opera", "vivaldi", "tor"]
history = []
old_hash = None
success = None
my_browser = None
task = input(": ")
prompt = f"here's the task: {task} if this is a browser task only output one word browser, if its not a browser task(for eg a desktop task) output one word desktop"
response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{'role': 'user', 'content': prompt}], temperature=0.1,max_tokens=100)
raw = response.choices[0].message.content
print(repr(raw))
if raw.lower() == "browser":
    for browser in browsers:
        if browser in task.lower():
            my_browser = browser
            break
    if my_browser != None:
        launch_browser(my_browser)
        webskt.connect()
        while True:
            cdp_elements = webskt.create_list()
            retries = 0
            while len(cdp_elements) == 0 and retries < 10:
                print("Page seems to have empty elements, waiting...")
                time.sleep(1.0)
                retries += 1#better to iterate 10 times for 1 second intervals than 5 tiems in 2 seconds intervals, maybe it gets resolved in 0.8 seconds and wait additional 1.2 for no reason.
                if retries == 10:
                    webskt.connect()
            title = webskt.get_title()
            url = webskt.get_url()
            data = AI.decide_cdp(cdp_elements, history, task, title, url)
            if data['action'] == "done":
                break
            if data.get('action') == 'click': #we do this to extract text of current id & to try, except as AI model sometimes hallucinates and output a string for an ID
                index = int(data['id'])
                if 0 <= index < len(cdp_elements):
                   data['text'] = cdp_elements[index]['text']
                else:
                    print(f"AI hallucinated id {data['id']}, forcing a wait")
                    data = {'action': 'wait'}
            old_url = url
            webskt.execute(cdp_elements, data['action'], data.get('url'), data.get('id'), data.get('text'), data.get('key'))
            if data['action'] == 'navigate':
                data['success'] = webskt.get_url() != old_url
            else:
                data['success'] = str(webskt.create_list()[:40]) != str(cdp_elements)
            history.append(data)
        print("Task Completed!")
    else:
        print("Specifiy browser name in you prompt!")


elif raw.lower() == "desktop":
    while not done:
        path = parser.capture()
        img, elements = parser.parse(path)
        img.save("/tmp/annotated.png")
        current_hash = imagehash.phash(img) #phash more appropriate for this, average_hash for even minor move movement hash value can change.
        browser_launched = False
        if old_hash is not None:
            difference = old_hash - current_hash
            print(difference)
            success =  difference >  7 #if nothing much changed, other than some anomalys(e.g time change), success is false
            data['success'] = success
        #AI decides
        data = AI.decide(elements, task, history) 
        if data.get('id') is not None:
            matching = next((e for e in elements if e['id'] == data['id']), None)
            if matching:
                data['id_text'] = matching['text']            
        history.append(data)
        done = execute(data, hand, parser, elements) 
        old_hash = current_hash
    print("Task Completed")

