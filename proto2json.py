import re
import os
import json


def read_proto(file):
    try:
        f = open(file, "r")
        lines = f.readlines()
        f.close()
    except FileNotFoundError:
        print("找不到文件：" + file)
        return False
    proto_name = os.path.basename(file).split(".")[0]
    need_import = []
    enum_dict = {}
    return_dict = {}
    prop_name = {}
    message_return_dict = {}
    message_prop_name = {}
    other_message = {}
    save = False
    for line in lines:
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
                save = False
                return_dict = {}
                prop_name = {}
                continue
            elif data_type == "message" or data_type == "enum":
                save = False
                return_dict = {}
                prop_name = {}
            if save:
                if save.startswith("enum_"):  # 1个proto2个enum?自己改吧。
                    enum_name = re.sub("enum_", "", save)
                    # data_id = int(re.findall("\d+", split_line[2])[0])
                    data_id = re.findall("\d+", split_line[2])[0]
                    if enum_name not in enum_dict:
                        enum_dict[enum_name] = {}
                    enum_dict[enum_name][data_id] = data_type
                else:
                    if len(split_line) > 3:  # 空行,忽略oneof
                        if len(split_line) == 4:
                            prop = split_line[1]
                            # data_id = int(re.findall("\d+", split_line[3])[0])
                            data_id = re.findall("\d+", split_line[3])[0]
                            return_dict[data_id] = data_type
                            prop_name[data_id] = prop
                        elif len(split_line) == 5:  # repeated and map
                            wire_type = re.sub("\\t", "", split_line[0])
                            if wire_type == "repeated":
                                data_type = split_line[1]
                                prop = split_line[2]
                                # data_id = int(re.findall("\d+", split_line[4])[0])
                                data_id = re.findall("\d+", split_line[4])[0]
                                return_dict[data_id] = "repeated_" + data_type
                                prop_name[data_id] = prop
                            else:
                                data_type = wire_type + split_line[1]
                                type_name = re.findall("map<(.*)>", data_type)[0]
                                type1, type2 = re.split(",", type_name)
                                prop = split_line[2]
                                # data_id = int(re.findall("\d+", split_line[4])[0])
                                data_id = re.findall("\d+", split_line[4])[0]
                                return_dict[data_id] = [type1, type2]
                                prop_name[data_id] = prop
                    if save == "message":
                        message_return_dict = return_dict
                        message_prop_name = prop_name
                    else:
                        if save not in other_message:
                            other_message[save] = [{}, {}]
                        other_message[save][0].update(return_dict)
                        other_message[save][1].update(prop_name)
            else:
                if data_type == "message":
                    if split_line[1] == proto_name:
                        save = "message"
                    else:
                        save = split_line[1]
                    continue
                elif data_type == "enum":
                    save = "enum_" + split_line[1]
                else:
                    continue

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
        elif isinstance(value, list):  # map应该没有第一位是需要导入类型的吧
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



