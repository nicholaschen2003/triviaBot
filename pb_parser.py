import json
import re

with open("2019-10-15-ALL.json", encoding='utf8') as json_file:
    for line in json_file.readlines():
        question = json.loads(line)
        with open(f'categories/{question["category"].lower()}.txt', 'a+', encoding='utf8') as outfile:
            try:
                temp = question["answer"]
                question["question"] = question["question"].strip().replace("\n", " ")
                question["answer"] = question["answer"].strip().replace("\n", " ")
                if x:= re.search(r'\{(.+?)\}', question["answer"]):
                    question["answer"] = x.group(1)
                question["answer"] = re.sub(r'(\[.+?\])', "", question["answer"]).strip()
                question["answer"] = re.sub(r'(\(.+?\))', "", question["answer"]).strip()
                outfile.write(f'{question["question"]}\n{question["answer"]}\n')
            except:
                pass