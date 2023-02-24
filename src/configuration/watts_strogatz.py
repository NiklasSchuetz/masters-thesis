import networkx as nx
import argparse


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION] ...",
        description="create a graphml file with the a watts-strogatz graph",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"{parser.prog} version 1.0.0"
    )
    parser.add_argument("-n", "--nodes", required=True)
    parser.add_argument("-k", "--mean_degree", required=True)
    parser.add_argument("-b", "--beta", required=True)
    parser.add_argument("-o", "--output", required=True)

    return parser


def main() -> None:
    parser = init_argparse()
    args = parser.parse_args()

    nodes = int(args.nodes)
    mean_degrees = int(args.mean_degree)
    beta = float(args.beta)

    try:
        network = nx.connected_watts_strogatz_graph(
            n=nodes, k=mean_degrees, p=beta, seed=15465464, tries=100
        )

        nx.write_graphml_lxml(network, f"{args.output}")
        return

    except nx.NetworkXError:
        print("Maximum number of tries for connected watts strogatz graph exceeded")


if __name__ == "__main__":
    main()
