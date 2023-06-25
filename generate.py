import re
import os
from typing import Literal


class Instance:
    Type: Literal["Enum", "Constant", "Class", "Function", "Member", "Hook"]
    Name: str
    Description: str
    Value: str
    Signature: str

    def __init__(self, text_info: str) -> None:
        for info in text_info.splitlines():
            name, value = re.findall(r"([^:]+):\s*(.*)", info)[0]
            if getattr(self, "Type", None) is None:
                self.Type = name
                self.Name = value
                if self.Type == "Enum":
                    self.Values: list[Instance] = []
                elif self.Type == "Class":
                    self.Functions: list[Instance] = []
                    self.Members: list[Instance] = []
                    self.Hooks: list[Instance] = []
            else:
                setattr(self, name, value)
        if getattr(self, "Description", None) is None:
            self.Description = ""


pretty_names = {
    "Enum": "Enums",
    "Constant": "Constants",
    "Class": "Classes",
    "Function": "Global Functions",
    "Hook": "Global Hooks",
}

with open("mapbase_7.1.txt", "r") as file:
    dump = file.read()

version, dump = dump.split("\n", 1)

server_text, client_text = dump.split("\nDOCUMENTATION_CLIENT\n")


def gather_info(raw: str):
    info: dict[str, dict[str, Instance]] = {
        "Enum": {},
        "Constant": {},
        "Class": {},
        "Function": {},
        "Hook": {},
    }
    for line in raw.split("\n\n"):
        line = re.sub(r"\n?={37}\n?", "", line)
        inst = Instance(line)
        # forgive me for this
        if (
            inst.Type == "Constant"
            and (enum_const := inst.Name.split(".")[0]) in info["Enum"].keys()
        ):
            info["Enum"][enum_const].Values.append(inst)
        if (
            inst.Type == "Function"
            and (class_func := inst.Name.split("::")[0]) in info["Class"].keys()
        ):
            info["Class"][class_func].Functions.append(inst)
        elif (
            inst.Type == "Member"
            and (class_member := inst.Name.split(".")[0]) in info["Class"].keys()
        ):
            info["Class"][class_member].Members.append(inst)
        elif (
            inst.Type == "Hook"
            and (class_hook := inst.Name.split(" -> ")[0]) in info["Class"].keys()
        ):
            info["Class"][class_hook].Hooks.append(inst)
        else:
            info[inst.Type][inst.Name] = inst

    return info


def generate_table(constants: list[Instance]):
    table = "| Name | Value | Description |\n| --- | --- | --- |\n"
    for constant in constants:
        table += f"| {constant.Name} | {constant.Value} |"
        if constant.Description:
            table += f" {constant.Description} |"
        table += "\n"
    return table + "\n"


def describe_signed(function: Instance, indents: int = 2):
    return_desc = "#" * indents + f" {function.Name}\n"
    if function.Description:
        return_desc += f"\n{function.Description}\n"
    return_desc += f"\n```cpp\n{function.Signature}\n```\n"
    return return_desc


def signed_page(signed_list: list[Instance], type: str):
    return f"### {type}\n\n" + (
        "\n".join(describe_signed(signed, 4) for signed in signed_list) + "\n"
    )


def generate_docs(info_dict: dict[str, dict[str, Instance]], category: str):
    return_list: list[str] = []
    for type, class_dict in info_dict.items():
        return_documentation = f"# VScript {category} {pretty_names[type]}, version {version}\n\nGenerated by Macosaro\n\n"
        for _, class_instance in class_dict.items():
            match type:
                case "Enum":
                    return_documentation += f"## {class_instance.Name}\n\n"
                    if class_instance.Description:
                        return_documentation += class_instance.Description + "\n"
                    return_documentation += generate_table(class_instance.Values)
                case "Class":
                    return_documentation += f"## {class_instance.Name}\n\n"
                    if class_instance.Description:
                        return_documentation += class_instance.Description + "\n\n"
                    if class_instance.Members:
                        return_documentation += signed_page(
                            class_instance.Members, "Members"
                        )
                    if class_instance.Functions:
                        return_documentation += signed_page(
                            class_instance.Functions, "Functions"
                        )
                    if class_instance.Hooks:
                        return_documentation += signed_page(
                            class_instance.Hooks, "Hooks"
                        )
                case _:
                    pass
        match type:
            case "Constant":
                return_documentation += generate_table(list(class_dict.values()))
            case "Function" | "Hook":
                return_documentation += (
                    "\n".join(
                        describe_signed(class_value)
                        for class_value in list(class_dict.values())
                    )
                    + "\n"
                )
            case _:
                pass
        
        return_list.append(return_documentation[:-1])

    return return_list


def write(path: str, content: str):
    with open(path, "w") as file:
        file.write(content)


server_docs = generate_docs(gather_info(server_text), "Server")
client_docs = generate_docs(gather_info(client_text), "Client")

if not os.path.exists("server"):
    os.mkdir("server")

write("server/enums.md", server_docs[0])
write("server/constants.md", server_docs[1])
write("server/classes.md", server_docs[2])
write("server/functions.md", server_docs[3])
write("server/hooks.md", server_docs[4])

if not os.path.exists("client"):
    os.mkdir("client")

write("client/enums.md", client_docs[0])
write("client/constants.md", client_docs[1])
write("client/classes.md", client_docs[2])
write("client/functions.md", client_docs[3])
write("client/hooks.md", client_docs[4])