
import json
from groq import Groq
import os 
from dotenv import load_dotenv
import time



class PilotBrain:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("api_key")
        self.client = Groq(api_key=self.api_key)

    def build_prompt(self, elements, task, history):
        lines = []
        for element in elements:
            line = f"- ID {element['id']}: '{element['text']}'"
            lines.append(line)
        elements_str = "\n".join(lines)
        if history:
            history_lines = []
            for i, h in enumerate(history, 1):
                action = history[i-1].get('action')
                if action == "type":
                    history_lines.append(f" Step {i}, typed: {h.get('text')} - {'working' if h.get('success') else 'no effect' if h.get('success') == False else "first action"}")
                elif action in  ('left', 'right'):
                    history_lines.append(f" Step {i}, clicked {h.get('action')}  {h.get('id_text')} - {'working' if h.get('success') else 'no effect' if h.get('success') == False else "first action"}")
                elif action == "key":
                    history_lines.append(f" Step {i}, clicked {h.get('key')} - {'working' if h.get('success') else 'no effect' if h.get('success') == False else "first action"}")
                elif action == "wait":
                    history_lines.append(f" Step {i}, waited")
                else:
                    history_lines.append(f" Step {i}, {h} - {'working' if h.get('success') else 'no effect' if h.get('success') == False else "first action"}")
            history_str = "\n".join(history_lines)
        else:
            history_str = "no history yet"
        #use Claude to write a good Prompt
        return (
            "You control a Linux(Ubuntu) desktop via mouse and keyboard.\n\n"
        "=== STRICT RULES ===\n"
        "1. After typing text, your NEXT action MUST be {\"action\":\"key\",\"key\":\"Return\"}.\n"
        "2. Do NOT type the same text you typed in the previous step.\n"
        "3. If the last 2 actions were identical, do {\"action\":\"wait\"} first.\n"
        "4. never click something twice in a row, for example if you see last action in history is left click, don't do left click again, do the next task, which is for example after left clicking on search bar on app menu is to search for app name\n"
        "5. - If your last action was a left click for eg, do NOT click again. do the next task after clicking.\n"
        "6- if your previous action had no effect, at the end it will be written to you - no effect, that means for example if you're told to enter a website, you typed url and want to go to the next step, but next to your typing url task it says - no effect, that means your attempt failed and you need to retry until its - worked\n"
        "7. Reply with ONLY one JSON object. No explanation, no markdown.\n\n"
        "=== STRATEGY ===\n"
        "- Is the app visible in the element list? → click its ID\n"
        "- Not visible? → click the search bar (look for 'Type to search'), type the name, then Return\n"
        "- Task done? → {\"action\":\"done\"}\n\n"
        f"=== TASK ===\n{task}\n\n"
        f"=== SCREEN ELEMENTS ===\n{elements_str}\n\n"
        f"=== WHAT YOU ALREADY DID ===\n{history_str}\n\n"
        "=== VALID ACTIONS ===\n"
        "- To left click an element:  {\"action\": \"left\", \"id\": <pick an id from the element list above>}\n"
        "- To right click an element: {\"action\": \"right\", \"id\": <pick an id from the element list above>}\n"
        "- To type text:              {\"action\": \"type\", \"text\": <the text you want to type>}\n"
        "- To press a keyboard key:   {\"action\": \"key\", \"key\": <key name, e.g. Return, Escape, Tab, BackSpace, Super>}\n"
        "- To wait and do nothing:    {\"action\": \"wait\"}\n"
        "- When the task is done:     {\"action\": \"done\"}\n\n"
        "Your next action:"
        )

    def decide(self, elements, task, history):
        prompt = self.build_prompt(elements, task, history)
        print(prompt)
        response = self.client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{'role': 'user', 'content': prompt}], temperature=0.1,max_tokens=100)
        raw = response.choices[0].message.content
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {'action': 'wait'} 
        return result
    
    def buildprompt_for_cdp(self, cdp_elements, history, task, title, url):
        lines = []
        for element in cdp_elements:
            line = f"id: {element['id']}, text: {element['text']}, selector: {element['selector']}"
            lines.append(line)
        elements_str = "\n".join(lines)
        if history:
            history_lines = []
            for i, h in enumerate(history, 1):
                action = history[i-1].get('action')
                id = h.get('id')
                if action.lower() == "click":
                    history_lines.append(f"Step {i}, clicked {h.get('text')}, {'working' if h.get('success') else "no effect" if h.get('success')==False else "first action"}")
                elif action.lower() == "value":
                    history_lines.append(f"Step {i}, wrote: {h.get('text')}, {'working' if h.get('success') else "no effect" if h.get('success')==False else "first action"}")
                elif action.lower() == "key":
                    history_lines.append(f"Step {i}, pressed {h.get('key')}, {'working' if h.get('success') else "no effect" if h.get('success')==False else "first action"}")
                elif action.lower() == "navigate":
                    history_lines.append(f"Step {i}, navigated to {h.get('url')}, {'working' if h.get('success') else "no effect" if h.get('success')==False else "first action"}")
                elif action.lower() == "wait":
                    history_lines.append("waited for 2 seconds")
                else:
                    history_lines.append(f"Step {i}, {h}, {'working' if h.get('success') else "no effect" if h.get('success')==False else "first action"}")
            history_str = "\n".join(history_lines)
        else:
            history_str = "No history yet, first entry"
        return (
    "You are controlling a web browser via Chrome DevTools Protocol.\n"
    "You act one step at a time. Think about where you are before acting.\n\n"

    "=== ENVIRONMENT ===\n"
    f"URL: {url}\n"
    f"Title: {title}\n\n"

    "=== TASK ===\n"
    f"{task}\n\n"

    "=== PAGE ELEMENTS ===\n"
    f"{elements_str}\n\n"

    "=== HISTORY ===\n"
    f"{history_str}\n\n"

    "=== RULES ===\n"
    "1. After typing into a field, next action MUST be {\"action\": \"key\", \"key\": \"Return\"}.\n"
    "2. If last action had no effect,wait and repeat it, if there's still no effect, do NOT repeat it — try something else.\n"
    "3. If you see a CAPTCHA or unexpected page, use {\"action\": \"wait\"}.\n"
    "4. The ID is always an integer.\n"
    "5. If page elements is empty, its usually the page is still loading, so just wait by setting action to wait until page elements isn't empty, don't hallucinate an id\n"
    "6. Reply with ONLY one JSON object. No explanation, no markdown, no code fences.\n\n"

    "=== VALID ACTIONS ===\n"
    "{\"action\": \"click\", \"id\": <id>}\n"
    "{\"action\": \"value\", \"id\": <id>, \"text\": \"<text>\"}\n"
    "{\"action\": \"key\", \"key\": \"<Return|Escape|Tab|BackSpace>\"}\n"
    "{\"action\": \"navigate\", \"url\": \"https://website.com\"}\n"
    "{\"action\": \"wait\"}\n"
    "{\"action\": \"done\"}\n\n"

    "Your next action:"
)
    def decide_cdp(self, elements, history, task, title, url):
        prompt = self.buildprompt_for_cdp(elements, history, task, title, url)
        print(prompt)
        response = self.client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{'role': 'user', 'content': prompt}], temperature=0.1,max_tokens=100)#temp 0.1 to reduce varance and creativity as its not needed here
        raw = response.choices[0].message.content
        print(raw)
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {'action': 'wait'} 
        return result
    
    
            
