"""The main command dispatcher"""

import argparse
from onnxcli import __doc__ as DESCRIPTION
from onnxcli.infer_shape import InferShapeCmd


def dispatch():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    subparsers = parser.add_subparsers(title='subcommands')

    # collect commands
    InferShapeCmd(subparsers)

    args = parser.parse_args()
    args.func(args)