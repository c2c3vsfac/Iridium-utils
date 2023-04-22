import os
import re
import json


file_path = os.getcwd()
file_path = file_path + "\\proto"
file_name = os.listdir(file_path)
packet = {}

for name in file_name:
    if name.endswith(".proto"):
        with open(file_path + "/" + name, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            if line.startswith("// CmdId:"): # 3.2-
            # if line.startswith("  //   CMD_ID"):  # 3.3
            # if line.strip().startswith("//	PEPPOHPHJOJ"): # 3.4
                packet_id = re.findall("\d+", line)[0]
                packet[packet_id] = os.path.splitext(name)[0]
                break

json_packet_id = json.dumps(packet, indent=1)
f = open("packet_id.json", "w")
f.write(json_packet_id)
f.close()