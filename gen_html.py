# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
data = json.load(open("data.json", encoding="utf-8"))
DATA_JSON = json.dumps(data, ensure_ascii=False)

TPL = open("template.html", encoding="utf-8").read()
html = TPL.replace("__DATA__", DATA_JSON)
open("index.html", "w", encoding="utf-8").write(html)
print("index.html 생성 완료 (", len(html), "bytes )")
