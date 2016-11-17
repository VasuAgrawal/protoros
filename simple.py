#!/usr/bin/env python3

# Example usage:
# protoc --plugin=protoc-gen-custom=simple.py --custom_out=. # protos/message.proto

import argparse

# http://www.expobrain.net/2016/09/13/create-a-plugin-for-google-protocol-buffer/
import sys
import itertools
import logging
import pprint
import ros_msg_parser

from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf.descriptor_pb2 import DescriptorProto, EnumDescriptorProto

class ProtoRosEq(object):
    _eqs = []
    proto_types = [
        "",
        "double",
        "float",
        "int64",
        "uint64",
        "int32",
        "fixed64",
        "fixed32",
        "bool",
        "string",
        "group",
        "message",
        "bytes",
        "uint32",
        "enum",
        "sfixed32",
        "sfixed64",
        "sint32",
        "sint64",
    ]

    def __init__(self, proto, ros):
        self._proto = proto
        self._ros = ros
        self._eqs.append(self)


    def __str__(self):
        return "{} = {}".format(self._proto, self._ros)


    @classmethod
    def find_eq(cls, type_name):
        for eq in cls._eqs:
            if eq._proto == type_name:
                return eq._ros
        return None


ProtoRosEq("double", "float64")
ProtoRosEq("float", "float32")
ProtoRosEq("int64", "int64")
ProtoRosEq("uint64", "uint64")
ProtoRosEq("int32", "int32")
ProtoRosEq("fixed64", "float64")
ProtoRosEq("fixed32", "float32")
ProtoRosEq("bool", "bool")
ProtoRosEq("string", "string")
ProtoRosEq("bytes", "uint8[]")
ProtoRosEq("uint32", "uint32")
ProtoRosEq("sfixed32", "int32")
ProtoRosEq("sfixed64", "int64")
ProtoRosEq("sint32", "int32")
ProtoRosEq("sint64", "int64")
ProtoRosEq(".google.protobuf.Timestamp", "time")
ProtoRosEq(".google.protobuf.Duration", "duration")

logging.error(pprint.pformat([str(eq) for eq in ProtoRosEq._eqs]) + "\n")

# Turns a field into a ROS message line
def parse_field(field):

    type_name = ProtoRosEq.proto_types[field.type]
    if type_name == "message" or type_name == "enum":
        type_name = field.type_name

    # Find the equivalence in ProtoRosEq
    name = ProtoRosEq.find_eq(type_name)
    return "{} {}".format(name, field.name)


def parse_message(message, response, package=""):
    complete_name = ".".join([package, message.name])
    complete_name = complete_name if complete_name.startswith(".") else "." + complete_name
    ProtoRosEq(complete_name, message.name)

    for enum in message.enum_type:
        parse_enum(enum, response, complete_name)

    f = response.file.add()
    f.name = message.name + ".msg"
    f.content = "\n".join(map(parse_field, message.field))

    logging.error(ros_msg_parser.RosMsg(text=f.content, package_name="package_name",
        message_name=message.name))
    # Ignore nested messages for now.


def parse_value(value):
    return "int32 {}={}".format(value.name, value.number)


def parse_enum(enum, response, package=""):
    # Enums are really just another type of message, with values rather than
    # fields. Not much difference otherwise.
    complete_name = ".".join([package, enum.name])
    complete_name = complete_name if complete_name.startswith(".") else "." + complete_name
    ProtoRosEq(complete_name, enum.name)
    
    f = response.file.add()
    f.name = enum.name + ".msg"
    f.content = "\n".join(map(parse_value, enum.value))


def parse_service(service, response):
    pass


def generate_convert_code(message, response):
    pass


def generate_code(request, response):
    # Request contains 3 things
    #   repeated string file_to_generate
    #   optional string parameter
    #   repeated FileDescriptorProto proto_file

    # Assuming parameters are passed in in the standard format, we can use an
    # argument parser to parse them.
    parser = argparse.ArgumentParser(description="Convert some stuff.")
    parser.add_argument("-p", "--package", type=str)
    args = parser.parse_args(request.parameter.split(" "))

    # Diagnostic information
    logging.info("Arguments: %s", args)
    logging.info("Generating from: %s", request.file_to_generate)

    # The proto file will probably contain some messages. We go through and try
    # to convert those.
    # See
    # https://github.com/google/protobuf/blob/master/src/google/protobuf/descriptor.proto
    for proto_file in request.proto_file:
        # eprint("Proto name   :", proto_file.name)
        # eprint("  Proto package:", proto_file.package)

        # The proto file will have some message types. Log those first.
        for message in proto_file.message_type:
            parse_message(message, response, package=proto_file.package)

        for enum in proto_file.enum_type:
            parse_enum(enum, response, package=proto_file.package)

        for service in proto_file.service:
            parse_service(service, response)

        # Only generate conversion code for messages in the files that the user
        # said to generate ROS messages for.
        if proto_file.name in request.file_to_generate:
            # eprint("Generating conversion code for", proto_file.name)

            for message in proto_file.message_type:
                generate_convert_code(message, response)


def main():
    # Initialize our ros message library
    ros_msg_parser.parse_messages("lib")

    # Read request message from stdin
    data = sys.stdin.buffer.read()

    # Parse request
    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(data)

    # Create response
    response = plugin.CodeGeneratorResponse()

    # Generate code
    generate_code(request, response)

    # Serialise response message and write to stdout
    output = response.SerializeToString()
    sys.stdout.buffer.write(output)


if __name__ == '__main__':
    main()
