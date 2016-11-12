#!/usr/bin/env python3

# Example usage:
# protoc --plugin=protoc-gen-custom=simple.py --custom_out=. # protos/message.proto


# http://www.expobrain.net/2016/09/13/create-a-plugin-for-google-protocol-buffer/
import sys

import itertools
import json

from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf.descriptor_pb2 import DescriptorProto, EnumDescriptorProto

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# Turns a field into a ROS message line
def parse_field(field):
    types = [
        "",         # 0
        "float64",  # "double",   # 1
        "float32",  # "float",    # 2
        "int64",    # "int64",    # 3
        "uint64",   # "uint64",   # 4
        "int32",    # "int32",    # 5
        "float64",  # "fixed64",  # 6
        "float32",  # "fixed32",  # 7
        "bool",     # "bool",     # 8
        "string",   # "string",   # 9
        "group",    # 10
        "message",  # 11
        "uint8[]",  # "bytes",    # 12
        "uint32",   # "uint32",   # 13
        "enum",     # 14
        "int32",    # "sfixed32", # 15
        "int64",    # "sfixed64", # 16
        "int32",    # "sint32",   # 17
        "int64",    # "sint64",   # 18
    ]

    name = (seen_messages[field.type_name] if field.type == 11 or
            field.type == 14 else types[field.type])
    return "{} {}".format(name, field.name)

seen_messages = dict()
def parse_message(message, response, package=""):
    complete_name = ".".join([package, message.name])
    complete_name = complete_name if complete_name.startswith(".") else "." + complete_name
    seen_messages[complete_name] = message.name
    eprint(complete_name)

    for enum in message.enum_type:
        parse_enum(enum, response, complete_name)

    f = response.file.add()
    f.name = message.name + ".msg"
    f.content = "\n".join(map(parse_field, message.field))
    # Ignore nested messages for now.

def parse_value(value):
    return "int32 {}={}".format(value.name, value.number)

def parse_enum(enum, response, package=""):
    # Enums are really just another type of message, with values rather than
    # fields. Not much difference otherwise.
    complete_name = ".".join([package, enum.name])
    complete_name = complete_name if complete_name.startswith(".") else "." + complete_name
    seen_messages[complete_name] = enum.name
    eprint("Adding %s, %s to seen" % (complete_name, enum.name))
    
    f = response.file.add()
    f.name = enum.name + ".msg"
    f.content = "\n".join(map(parse_value, enum.value))


def parse_service(service, response):
    pass

def generate_code(request, response):
    # Request contains 3 things
    #   repeated string file_to_generate
    #   optional string parameter
    #   repeated FileDescriptorProto proto_file
    
    # The proto file will probably contain some messages. We go through and try
    # to convert those.
    # See
    # https://github.com/google/protobuf/blob/master/src/google/protobuf/descriptor.proto

    for proto_file in request.proto_file:
        eprint("Proto name   :", proto_file.name)
        eprint("Proto package:", proto_file.package)

        # The proto file will have some message types. Log those first.
        for message in proto_file.message_type:
            parse_message(message, response, package=proto_file.package)

        for enum in proto_file.enum_type:
            parse_enum(enum, response)

        for service in proto_file.service:
            parse_service(service, response)

if __name__ == '__main__':
    # Read request message from stdin
    data = sys.stdin.buffer.read()

    # Parse request
    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(data)

    # Create response
    response = plugin.CodeGeneratorResponse()

    # Generate code
    generate_code(request, response)

    # Serialise response message
    output = response.SerializeToString()

    # Write to stdout
    sys.stdout.buffer.write(output)
