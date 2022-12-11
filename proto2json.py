import re
import os
import json


def read_proto(file):
    try:
        with open(file, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("找不到文件：" + file)
        return False
    proto_name = os.path.basename(file).split(".")[0]
    need_import = []
    enum_dict = {}
    message_return_dict = {}
    message_prop_name = {}
    other_message = {}
    save = []
    for line in lines:
        if not line.startswith("  //"):
            if line.startswith("import"):
                file_whole_name = re.findall(r'"(.*)"', re.split(" ", line)[1])[0]
                file_name = re.sub(".proto", "", file_whole_name)
                need_import.append(file_name)
            else:
                # 解的proto有时用\t有时用空格
                no_left_space_line = line.lstrip()
                split_line = re.split(" ", no_left_space_line)
                data_type = re.sub("\\t", "", split_line[0])
                if data_type == "}\n":
                    if save:  # oneof 会有多余的括号
                        if save[-1][0] == "message":
                            if save[-1][1] == proto_name:
                                message_return_dict = save[-1][2]
                                message_prop_name = save[-1][3]
                            else:
                                other_message[save[-1][1]] = [save[-1][2], save[-1][3]]
                            save.pop(-1)
                        elif save[-1][0] == "enum":
                            enum_dict[save[-1][1]] = save[-1][2]
                            save.pop(-1)
                    continue
                elif data_type == "message":
                    save.append((data_type, split_line[1], {}, {}))
                    continue
                elif data_type == "enum":
                    save.append((data_type, split_line[1], {}))
                    continue
                if save:
                    if save[-1][0] == "enum":
                        data_id = re.findall("\d+", split_line[2])[0]
                        save[-1][2][data_id] = data_type
                    else:
                        if len(split_line) > 3:  # 空行,忽略oneof
                            if len(split_line) == 4:
                                prop = split_line[1]
                                data_id = re.findall("\d+", split_line[3])[0]
                                save[-1][2][data_id] = data_type
                                save[-1][3][data_id] = prop
                            elif len(split_line) == 5:  # repeated and map
                                wire_type = re.sub("\\t", "", split_line[0])
                                if wire_type == "repeated":
                                    data_type = split_line[1]
                                    prop = split_line[2]
                                    data_id = re.findall("\d+", split_line[4])[0]
                                    save[-1][2][data_id] = "repeated_" + data_type
                                    save[-1][3][data_id] = prop
                                else:
                                    data_type = wire_type + split_line[1]
                                    type_name = re.findall("map<(.*)>", data_type)[0]
                                    type1, type2 = re.split(",", type_name)
                                    prop = split_line[2]
                                    data_id = re.findall("\d+", split_line[4])[0]
                                    save[-1][2][data_id] = [type1, type2]
                                    save[-1][3][data_id] = prop
    return need_import, enum_dict, message_return_dict, message_prop_name, other_message


def convert(proto_name):
    file_path = os.getcwd()
    proto_name = file_path + "\\proto\\" + proto_name + ".proto"
    need_import, enum_dict, encoding_rules, prop_name, other_message = read_proto(proto_name)
    for key, value in encoding_rules.items():
        if value in need_import:
            enum_dict, d_rule, d_name = convert(value)
            if value in enum_dict:
                encoding_rules[key] = "enum"
                prop_name[key] = {prop_name[key]: enum_dict[value]}
            else:
                encoding_rules[key] = [d_rule, d_name]
        elif isinstance(value, list):  # map第一位只能为整数或字符串
            if value[1] in need_import:
                _, d_rule, d_name = convert(value[1])
                encoding_rules[key] = {"map": [value[0], [d_rule, d_name]]}
            else:
                encoding_rules[key] = {"map": value}
        elif re.sub("repeated_", "", value) in need_import:
            _, d_rule, d_name = convert(re.sub("repeated_", "", value))
            encoding_rules[key] = {"repeated": [d_rule, d_name]}
        elif value in other_message:
            encoding_rules[key] = other_message[value][0]
            prop_name[key] = other_message[value][1]
        elif re.sub("repeated_", "", value) in other_message and value.startswith("repeated_"):
            encoding_rules[key] = {"repeated": [other_message[re.sub("repeated_", "", value)][0],
                                                other_message[re.sub("repeated_", "", value)][1]]}
        elif value in enum_dict:
            encoding_rules[key] = "enum"
            prop_name[key] = {prop_name[key]: enum_dict[value]}
    return enum_dict, encoding_rules, prop_name


f = open("packet_id.json", "r")
d_pkt_id = json.load(f)
f.close()
last_key = list(d_pkt_id.keys())[-1]
f = open("packet_serialization.json", "w")
f.write("{\n")
for key, value in d_pkt_id.items():
    _, encoding_rules, prop_names = convert(value)
    f.write(json.dumps(key) + ": " + json.dumps([encoding_rules, prop_names]))
    if key == last_key:
        f.write("\n")
    else:
        f.write(",\n")
f.write("}")
f.close()

# UnionCmdNotify
# ***********************************************************
# f = open("packet_id_unioncmdnotify2.json", "r")
# d_pkt_id = json.load(f)
# f.close()
# last_key = list(d_pkt_id.keys())[-1]
# i = 0
# fw = open("ucn_id.json", "w")
# fw2 = open("ucn_serialization.json", "w")
# fw.write("{\n")
# fw2.write("{\n")
# for key, value in d_pkt_id.items():
#     if not value.startswith("1"):
#         fw.write(json.dumps(key) + ": " + json.dumps(str(i + 10000)))
#         if key == last_key:
#             fw.write("\n")
#         else:
#             fw.write(",\n")
#         _, encoding_rules, prop_names = convert(value)
#         fw2.write(json.dumps(str(i + 10000)) + ": " + json.dumps([encoding_rules, prop_names]))
#         if key == last_key:
#             fw2.write("\n")
#         else:
#             fw2.write(",\n")
#         i += 1
# fw.write("}")
# fw2.write("}")
# fw.close()
# fw2.close()
# ***********************************************************

# guess_which_file
# ***********************************************************
def judge_type(prop_name):
    zero = ["int32", "int64", "uint32", "uint64", "sint32", "sint64", "bool", "enum"]
    one = ["fixed64", "sfixed64", "double"]
    five = ["fixed32", "sfixed32", "float"]
    if prop_name in zero:
        return 0
    elif prop_name in one:
        return 1
    elif prop_name in five:
        return 5
    else:
        return 2


# file_path = os.getcwd()
# file_path = file_path + "\\proto\\"
# files = os.listdir(file_path)
# for file in files:
#     file_name = file.replace(".proto", "")
#     _, rule, _ = convert(file_name)
#     if "2" in rule:
#         if rule["2"] == "uint32":
#             print(file_name)

# ***********************************************************

