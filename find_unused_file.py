import os
import json
import re


def find_unused_file(proto_name):
    full_proto_name = proto_name + ".proto"
    if full_proto_name in proto_names:
        proto_names.remove(full_proto_name)

    full_file_path = file_path + "\\proto\\" + proto_name + ".proto"
    need_import = []
    f = open(full_file_path, "r")
    lines = f.readlines()
    f.close()
    for line in lines:
        if line.startswith("import"):
            file_whole_name = re.findall(r'"(.*)"', re.split(" ", line)[1])[0]
            file_name = re.sub(".proto", "", file_whole_name)
            need_import.append(file_name)
    if need_import:
        for import_name in need_import:
            find_unused_file(import_name)


file_path = os.getcwd()
proto_names = os.listdir(file_path + "\\proto")
f_pkg_id = open("packet_id.json", "r")
pkg_ids = json.load(f_pkg_id)
f_pkg_id.close()

for pkg_id, name in pkg_ids.items():
    find_unused_file(name)
print(proto_names)

