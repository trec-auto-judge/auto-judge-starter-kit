#!/usr/bin/env python3
import json

with open("ragtime25_main_eng.jsonl", "r") as f_in, open("topics.jsonl", "w") as f_out:
    for l in f_in:
        l = json.loads(l)
        m = {"original_topic": l}

        m["request_id"] = l["request_id"]
        m["id"] = l["request_id"]
        m["title"] = l["title"]
        m["narrative"] = l["title"]
        f_out.write(json.dumps(m) + "\n")
