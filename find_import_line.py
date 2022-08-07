import os
import json
import re


def find_need_import(proto_name, offset=0):
    full_file_path = file_path + "\\proto\\" + proto_name + ".proto"
    need_import = []
    import_line = proto_name
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
            space_num = offset + len(proto_name) + 2
            if offset == 0:  # 第一个前面没有箭头，不需要+2
                space_num -= 2
            extend_line = find_need_import(import_name, space_num)
            import_line += "->" + extend_line
            if import_name != need_import[-1]:
                import_line += "\n" + " " * space_num
    return import_line


file_path = os.getcwd()
proto_names = os.listdir(file_path + "\\proto")
f_pkg_id = open("packet_id.json", "r")
pkg_ids = json.load(f_pkg_id)
f_pkg_id.close()

for pkg_id, name in pkg_ids.items():
    print(find_need_import(name))

