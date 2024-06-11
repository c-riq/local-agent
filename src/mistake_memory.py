import json
from re import M
import ollama


SYSTEM_PROMPT_MISTAKES = '''
You are an experienced software engineer and generate recommendations from mistakes. If a similar recommendation already exists in the aggregated data already, then output the existing recommendation otherwise generate a new recommendation to prevent the given error

Examples:
In: {"existingRecommendations": ["do not try to import files which may not exists"], "error":"Error: File 'example.jpg' does not exist"}
Out: do not try to import files which may not exists

In: {"existingRecommendations": ["do not try to import files which may not exists"],"error":"Traceback (most recent call last):\nFile \"/home/t/code_samples/main.py\", line 2, in <module>\nnumbers[4]\nIndexError: list index out of range"}
Out: Ensure that the index you're accessing falls within the sequence's valid range
'''

class MistakeMemory:
    def __init__(self):
        try:
            with open("common_mistakes.json", "r") as f:
                self.common_mistakes = json.load(f)
        except:
            self.common_mistakes = {}

    def increment_mistake(self, m):
        if m in self.common_mistakes.keys():
            self.common_mistakes[m] += 1
        else:
            self.common_mistakes[m] = 1
        with open("common_mistakes.json", "w") as f:
            json.dump(self.common_mistakes, f)

    def get_top_n_advice(self, n):
        sorted_mistakes = sorted(self.common_mistakes.items(), key=lambda x: x[1], reverse=True)
        return [key for key, _ in sorted_mistakes][:n]

    def remember_mistake(self, error):
        prompt = json.dumps({"existingRecommendations": [k  for  k in  self.common_mistakes.keys()], "error": str(error)})
        response = ollama.generate(model='llama3',system=SYSTEM_PROMPT_MISTAKES, prompt=prompt)
        self.increment_mistake(response["response"])
        return response
    
