
from hand import WaylandPortalHand
from screen import ScreenParser
from brain import PilotBrain
import time

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

if __name__ == "__main__":
    hand = WaylandPortalHand()
    parser = ScreenParser()
    AI = PilotBrain()

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

    done = False
    history = []
    task = input(": ")
    while not done:
        path = parser.capture()
        img, elements = parser.parse(path)
        img.save("/tmp/annotated.png")
        #AI decides
        data = AI.decide(elements, task, history)
        history.append(data)
        done = execute(data, hand, parser, elements)
    print("Task Completed")