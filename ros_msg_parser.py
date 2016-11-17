# Parse ros messages from a given directory.

import os
import re
import sys
import logging

class RosMsgField(object):
    _primitives = set([
        "bool",
        "int8",
        "uint8",
        "int16",
        "uint16",
        "int32",
        "uint32",
        "int64",
        "uint64",
        "float32",
        "float64",
        "string",
        "time",
        "duration",
        "char", # Deprecated alias for uint8
        "byte", # Deprecated alias for uint8
    ])


    def __init__(self, package_name, line):
        terms = [item.strip() for item in line.split("#")[0].split(" ")
                 if item.strip()]

        self._name = terms[1]
        self._name_value = ""
        if "=" in self._name:
            split = self._name.split("=")
            self._name = split[0]
            self._name_value = split[1]

        type_name = terms[0]
        array_matcher = re.compile(r"\[[0-9]*\]")
        match = array_matcher.search(type_name)
        self._array = bool(match)

        if match:
            arr = match.group()
            self._array_num = int(arr[1:-1]) if len(arr) > 2 else -1

        self._type = (type_name[:-(len(self._array_str()))]
                      if self._array else type_name)

        # Header is a special case in ROS
        if (self._type == "Header" and self._name == "header"
                and not self._array):
            self._type = "std_msgs/Header"

        # If it's not a primitive or already classified, give it a class
        if "/" not in self._type and self._type not in self._primitives:
            self._type = "/".join([package_name, self._type])


    def _array_str(self):
        if self._array:
            return "".join([
                "[",
                str(self._array_num) if self._array_num > -1 else "",
                "]"])
        else:
            return ""


    def __str__(self):
        # return self._type + self._array_str() +  " " + self._name
        return str([self._type, self._array_str(), self._name,
            self._name_value])


    @classmethod
    def get_primitives(cls):
        return cls._primitives


    def get_type(self):
        return self._type


class RosMsg(object):
    # Turn a file path into a message
    def __init__(self, path="", text="", package_name="", message_name=""):
        if path:
            self._check_path(path)
            self._read_fields(path)
        elif text and package_name and message_name:
            self._package_name = package_name
            self._message_name = message_name
            self._fields = [RosMsgField(self._package_name, line) for line in
                            text.splitlines() if line.strip().split("#")[0]]
        else:
            raise Exception("Wrong set of arguments")


    def _check_path(self, path):
        path = os.path.abspath(path)

        message_name = os.path.basename(path)
        if not path.endswith(".msg"):
            raise Exception("File %s has invalid file type!" % message_name)
        message_name = message_name[:-4]

        p = os.path.basename(os.path.dirname(path))
        if p != "msg":
            raise Exception("Path: %s, File not contained inside msg directory!"
                            % path)

        package_name = os.path.basename(os.path.dirname(os.path.dirname(path)))
        if not package_name:
            raise Exception("Unable to find package name")

        self._message_name = message_name
        self._package_name = package_name


    def _read_fields(self, path):
        self._fields = []
        with open(path) as f:
            for line in f.readlines():
                if line.strip().split("#")[0]:
                    self._fields.append(RosMsgField(self._package_name, line))


    def __str__(self):
        name = "NODE: %s\n" % self.get_type()
        fields = "\n".join(["\t%s" % str(field) for field in self._fields])
        return name + fields + "\n"
    
    def get_type(self):
        return "/".join([self._package_name, self._message_name])


    def verify_fields(self, types):
        for field in self._fields:
            if field.get_type() not in types: return False, field.get_type()
        return True, self.get_type()


msgs = []
types = set(RosMsgField.get_primitives())


def parse_messages(lib_dir):
    for root, dirs, files in os.walk(lib_dir):
        for f in files:
            try:
                msgs.append(RosMsg(os.path.join(root, f)))
                types.add(msgs[-1].get_type())
            except Exception as e:
                # logging.error(e)
                pass

    # Now we need to verify that the entire set of messages is parseable
    for msg in msgs:
        status, t = msg.verify_fields(types)
        if not status:
            raise Exception("Unable to find %s" % t)

    logging.info("Verified all of the messages in the provided folder")


def main():
    parse_messages("lib")


if __name__ == "__main__":
    main()
