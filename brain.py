
import json
from groq import Groq
import os 
from dotenv import load_dotenv
import time



class PilotBrain:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY")
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
                    history_lines.append(f" Step {i}, typed: {h.get('text')}")
                elif action in  ('left', 'right'):
                    history_lines.append(f" Step {i}, clicked {h.get('action')} with ID: {h.get('id')}")
                elif action == "key":
                    history_lines.append(f" Step {i}, clicked {h.get('key')}")
                elif action == "wait":
                    history_lines.append(f" Step {i}, waited")
                else:
                    history_lines.append(f" Step {i}, {h}")
            history_str = "\n".join(history_lines)
        else:
            history_str = "no history yet"
        #used Claude to write a good Prompt
        return (
            "You control a Linux(Ubuntu) desktop via mouse and keyboard.\n\n"
        "=== STRICT RULES ===\n"
        "1. After typing text, your NEXT action MUST be {\"action\":\"key\",\"key\":\"Return\"}.\n"
        "2. Do NOT type the same text you typed in the previous step.\n"
        "3. If the last 2 actions were identical, do {\"action\":\"wait\"} first.\n"
        "4. never click something twice in a row, for example if you see last action in history is left click, don't do left click again, do the next task, which is for example after left clicking on search bar on app menu is to search for app name\n"
        "5. - If your last action was a left click for eg, do NOT click again. do the next task after clicking.\n"
        "6. Reply with ONLY one JSON object. No explanation, no markdown.\n\n"
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
        "- To press a keyboard key:   {\"action\": \"key\", \"key\": <key name, e.g. Return, Escape, Tab, BackSpace>}\n"
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
    
    
            
