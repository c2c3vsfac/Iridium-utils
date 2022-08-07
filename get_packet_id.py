import os
import re
import json


file_path = os.getcwd()
file_path = file_path + "\\proto"
file_name = os.listdir(file_path)
packet = {}

for name in file_name:
    f = open(file_path + "/" + name, "r")
    lines = f.readlines()
    f.close()
    for line in lines:
        if line.startswith("// CmdId:"):
            packet_id = re.findall("\d+", line)[0]
            packet[packet_id] = os.path.splitext(name)[0]
            continue

json_packet_id = json.dumps(packet)
f = open("packet_id.json", "w")
f.write(json_packet_id)
f.close()

