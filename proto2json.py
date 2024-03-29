import re
import os
import json


def read_proto(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
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
    one_of_ignore = False
    for line in lines:
        line = line.lstrip()
        if not line.startswith("//"):
            # 去掉注释
            end_pos = line.find(";")
            if end_pos != -1:
                line = line[:end_pos + 1]

            # 解的proto有时用\t有时用空格
            split_line = re.split(" ", line)
            split_line = [each for each in split_line if each] # 连续多空格
            if line.startswith("import"):
                file_whole_name = re.findall(r'"(.*)"', split_line[1])[0]
                file_name = re.sub(".proto", "", file_whole_name)
                need_import.append(file_name)
                continue
            elif line.startswith("message"):
                save.append((split_line[0], split_line[1], {}, {}))
                continue
            elif line.startswith("enum"):
                save.append((split_line[0], split_line[1], {}))
                continue
            elif line.startswith("oneof"):
                one_of_ignore = True
                continue
            elif line.startswith("}\n") or line.startswith("}"):
                if one_of_ignore:  # oneof 会有多余的括号
                    one_of_ignore = False
                else:
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
            if save:
                if save[-1][0] == "enum":
                    data_id = re.findall("\d+", split_line[2])[0]
                    save[-1][2][data_id] = split_line[0]
                else:
                    if len(split_line) > 3:  # 空行,忽略oneof
                        if split_line[0] == 'optional':
                            split_line.pop(0)
                        if len(split_line) == 4:
                            prop = split_line[1]
                            data_id = re.findall("\d+", split_line[3])[0]
                            save[-1][2][data_id] = split_line[0]
                            save[-1][3][data_id] = prop
                        elif len(split_line) == 5:  # repeated and map
                            if split_line[0] == "repeated":
                                data_type = split_line[1]
                                prop = split_line[2]
                                data_id = re.findall("\d+", split_line[4])[0]
                                save[-1][2][data_id] = "repeated_" + data_type
                                save[-1][3][data_id] = prop
                            else:
                                data_type = split_line[0] + split_line[1]
                                type_name = re.findall("map<(.*)>", data_type)[0]
                                type1, type2 = re.split(",", type_name)
                                prop = split_line[2]
                                data_id = re.findall("\d+", split_line[4])[0]
                                save[-1][2][data_id] = [type1, type2]
                                save[-1][3][data_id] = prop
    return need_import, enum_dict, message_return_dict, message_prop_name, other_message


def convert(proto_name):
    current_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.dirname(current_path)
    proto_name = file_path + "\\proto\\" + proto_name + ".proto"
    # print("now_proto_name: %s" % proto_name)
    need_import, enum_dict, encoding_rules, prop_name, other_message = read_proto(proto_name)
    for key, value in encoding_rules.items():
        # print("er:" + str(encoding_rules))
        # print("pn:" + str(prop_name))
        if value in need_import:
            import_enum_dict, d_rule, d_name = convert(value)
            if value in import_enum_dict:
                encoding_rules[key] = "enum"
                prop_name[key] = {prop_name[key]: import_enum_dict[value]}
            else:
                encoding_rules[key] = [d_rule, d_name]
        elif isinstance(value, list):  # map第一位只能为整数或字符串
            if value[1] in need_import:
                import_enum_dict, d_rule, d_name = convert(value[1])
                if value[1] in import_enum_dict:
                    encoding_rules[key] = {"map": [value[0], ["enum", import_enum_dict[value[1]]]]}
                else:
                    encoding_rules[key] = {"map": [value[0], [d_rule, d_name]]}
            else:
                encoding_rules[key] = {"map": value}
        elif re.sub("repeated_", "", value) in need_import:
            need_import_proto_name = value.replace("repeated_", "")
            import_enum_dict, d_rule, d_name = convert(need_import_proto_name)
            if need_import_proto_name in import_enum_dict:
                encoding_rules[key] = "repeated_enum"
                prop_name[key] = [prop_name[key], import_enum_dict[need_import_proto_name]]
            else:
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


f = open("packet_id.json", "r", encoding="utf-8")
d_pkt_id = json.load(f)
f.close()
last_key = list(d_pkt_id.keys())[-1]
f = open("packet_serialization.json", "w", encoding="utf-8")
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
# f = open("ucn_match.json", "r")
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
#         fw.write(json.dumps(key) + ": " + json.dumps(str(i + 100000)))
#         if key == last_key:
#             fw.write("\n")
#         else:
#             fw.write(",\n")
#         _, encoding_rules, prop_names = convert(value)
#         fw2.write(json.dumps(str(i + 100000)) + ": " + json.dumps([encoding_rules, prop_names]))
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
#     _, _, rule, name, _ = read_proto(file_path + file)
#     # file_name = file.replace(".proto", "")
#     # _, rule, _ = convert(file_name)
#     if len(rule) == 5:
#         l_rule = list(rule.values())
#         satisfy = True
#         for each in l_rule:
#             if isinstance(each, str):
#                 pass
#             else:
#                 satisfy = False
#                 break
#         print(file)
#         if satisfy:
#             if set(l_rule) == {"uint32", "int32"}:
#     # if "3" in rule and "12" in rule and "15" in rule:
#         # if rule["2"] == "uint32":
#         # if judge_type(rule["3"]) == 2 and judge_type(rule["12"]) == 2 and judge_type(rule["15"]) == 2:
#                 print(file)
# print(convert("AbilityChangeNotify"))
# DEOFBFHGCBD.proto -> AbilityMetaSpecialFloatArgument
# ***********************************************************
# proto_preprocess
# from iridium_utils import extract_text_current_line_from_file
# file_path = os.getcwd()
# file_path = file_path + "\\proto"
# file_name = os.listdir(file_path)
# packet = {}
#
# for name in file_name:
#     f = open(file_path + "/" + name, "r")
#     text = f.read()
#     result = text.find("PEPPOHPHJOJ")
#     f.close()
#     if result != -1:
#         line_packet_id = extract_text_current_line_from_file(text, "PEPPOHPHJOJ")
#         packet_id = re.findall("\d+", line_packet_id)[0]
#         pre_text = text[:result]
#         reverse_pre_text = pre_text[::-1]
#         start_location = reverse_pre_text.find("{")
#         start_location = len(pre_text) - start_location
#         pre_text = text[:start_location]
#         reverse_pre_text = pre_text[::-1]
#         start_location = reverse_pre_text.find("\n")
#         start_location = len(pre_text) - start_location
#         end_location = text.find("}", result)
#         text = text.replace(text[start_location: end_location + 1], "")
#         f = open(file_path + "/" + name, "w", encoding="utf-8")
#         f.write("// " + packet_id + "\n")
#         f.write(text)
#         f.close()


