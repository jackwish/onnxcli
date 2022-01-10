import logging
import onnx
from onnxcli.common import SubCmd, dtype, shape

logger = logging.getLogger('onnxcli')


class InspectCmd(SubCmd):
    """Prints the information of nodes tensors of the given model.

    When working on deep learning, you may like to take a look at what's inside the model.
    You no longer need to scroll the Netron window to look for nodes or tensors.
    Instead, you can dump the node attributes and tensor values with a single command.
    """

    subcmd = 'inspect'

    def add_args(self, subparser):
        subparser.add_argument('input_path', type=str, help="The input ONNX model")
        subparser.add_argument(
            '-m',
            '--meta',
            action='store_true',
            help="Print the meta information of the model",
        )
        subparser.add_argument(
            '-n',
            '--node',
            action='store_true',
            help="Print the node information of the model",
        )
        subparser.add_argument(
            '-t',
            '--tensor',
            action='store_true',
            help="Print the tensor information of the model",
        )
        subparser.add_argument(
            '-i',
            '--indices',
            type=int,
            nargs="+",
            default=[],
            help="Specify the indices of the node(s) or tensor(s) to inspect." " Can NOT set together with --names",
        )
        subparser.add_argument(
            '-N',
            '--names',
            type=str,
            nargs="+",
            default=[],
            help="Specify the names of the node(s) or tensor(s) to inspect." " Can NOT set together with --indices",
        )
        subparser.add_argument(
            '-d',
            '--detail',
            action='store_true',
            help="Print detailed information of the nodes or tensors that specified by --indices or --names."
            " Warning: will print the data of tensors.",
        )

    def run(self, args):
        logger.info("Running <Inspect> on model {}".format(args.input_path))
        has_indices = len(args.indices) != 0
        has_names = len(args.names) != 0
        no_tensor_or_node = args.node is None and args.tensor is None
        if has_indices and has_names:
            raise ValueError("Can NOT set both --indices and --names")
        if (has_indices or has_indices) and no_tensor_or_node:
            raise ValueError("Can NOT set --indices or --names without --node or --tensor")
        if (not has_indices and not has_names) and args.detail:
            raise ValueError("Can NOT set --detail without --indices or --names")

        try:
            onnx.checker.check_model(args.input_path)
        except Exception:
            logger.warn("Failed to check model {}, statistic could be inaccurate!".format(args.input_path))
        m = onnx.load_model(args.input_path)
        g = m.graph
        printed_any = False

        if args.meta:
            print_meta(m)
            printed_any = True

        if args.node:
            print_nodes(g, args.indices, args.names, args.detail)
            printed_any = True

        if args.tensor:
            print_tensor(g, args.indices, args.names, args.detail)
            printed_any = True

        if not printed_any:
            print_basic(args, g)


def print_meta(m):
    print("Meta information:")
    print("-" * 80)
    print("  IR Version: {}".format(m.ir_version))
    print("  Opset Import: {}".format(m.opset_import))
    print("  Producer name: {}".format(m.producer_name))
    print("  Producer version: {}".format(m.producer_version))
    print("  Domain: {}".format(m.domain))
    print("  Doc string: {}".format(m.doc_string))
    for i in m.metadata_props:
        print("  meta.{} = {}", i.key, i.value)


def print_basic(g):
    print("  Graph name: {}".format(len(g.name)))
    print("  Graph inputs: {}".format(len(g.input)))
    print("  Graph outputs: {}".format(len(g.output)))
    print("  Nodes in total: {}".format(len(g.node)))
    print("  ValueInfo in total: {}".format(len(g.value_info)))
    print("  Initializers in total: {}".format(len(g.initializer)))
    print("  Sparse Initializers in total: {}".format(len(g.sparse_initializer)))
    print("  Quantization in total: {}".format(len(g.quantization_annotation)))


def print_tensor(g, indices, names, detail):
    print("Tensor information:")
    print("-" * 80)

    def print_value_info(t):
        txt = "  ValueInfo \"{}\":".format(t.name)
        txt += " type {},".format(dtype(t.type.tensor_type.elem_type))
        txt += " shape {},".format(shape(t.type.tensor_type.shape))
        print(txt)

    def print_initializer(t, detail):
        txt = "  Initializer \"{}\":".format(t.name)
        txt += " type {},".format(dtype(t.data_type))
        txt += " shape {},".format(t.dims)
        print(txt)
        if detail:
            print("    float data: {}".format(t.float_data))

    # print with indices
    if len(indices) > 0:
        for idx in indices:
            printed_any = False
            if idx < len(g.value_info):
                printed_any = True
                print_value_info(g.value_info[idx])
            if idx < len(g.initializer):
                print_initializer(g.initializer[idx], detail)
                printed_any = True
            if idx < len(g.input):
                print_value_info(g.input[idx])
                printed_any = True
            if idx < len(g.output):
                print_value_info(g.output[idx])
                printed_any = True
            if not printed_any:
                raise ValueError("indices {} out of range, check the total size of tensors")
        return

    # print with names
    if len(names) > 0:
        printed_any = False
        for name in names:
            for i in g.value_info:
                if i.name == name:
                    print_value_info(i)
                    printed_any = True
                    break
            for i in g.initializer:
                if i.name == name:
                    print_initializer(i, detail)
                    printed_any = True
                    break
            for i in g.input:
                if i.name == name:
                    print_value_info(i)
                    printed_any = True
                    break
            for i in g.output:
                if i.name == name:
                    print_value_info(i)
                    printed_any = True
                    break
        if not printed_any:
            raise ValueError("No tensor found with name {}".format(name))
        return

    # print all tensors
    for t in g.value_info:
        print_value_info(t)
    for t in g.initializer:
        print_initializer(t, False)


def print_nodes(g, indices, names, detail):
    print("Node information:")
    print("-" * 80)

    def print_node(n, detail):
        txt = "  Node \"{}\":".format(n.name)
        txt += " type \"{}\",".format(n.op_type)
        txt += " inputs \"{}\",".format(n.input)
        txt += " outputs \"{}\"".format(n.output)
        print(txt)
        if detail and len(n.attribute) > 0:
            print("    attributes: {}".format(n.attribute))

    # print with indices
    if len(indices) > 0:
        for idx in indices:
            if idx >= len(g.node):
                raise ValueError("indices {} out of range, node in total {}".format(idx, len(g.node)))
            print_node(g.node[idx], detail)
        return

    # print with names
    if len(names) > 0:
        found_any = False
        for name in names:
            for n in g.node:
                if n.name == name:
                    print_node(n, detail)
                    found_any = True
                    break
        if not found_any:
            raise ValueError("No node found with name {}".format(name))
        return

    import collections

    ops = collections.Counter([node.op_type for node in g.node])
    for op, count in ops.most_common():
        print("  Node type \"{}\" has: {}".format(op, count))

    print("-" * 80)
    for node in g.node:
        print_node(node, False)
