from configparser import ConfigParser
from argparse import ArgumentParser
import networkx as nx
import numpy as np
import os


def init_argparse() -> ArgumentParser:
    parser = ArgumentParser(
        usage="%(prog)s [OPTION] ...",
        description="create a .ini file for the control node",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"{parser.prog} version 1.0.0"
    )
    parser.add_argument("-t", "--type", required=True)
    parser.add_argument("-ti", "--time", required=True)

    parser.add_argument("-c", "--coupling_strength")
    parser.add_argument("-cs", "--cs")
    parser.add_argument("-s", "--max_states")

    parser.add_argument("-o", "--out_dir", default="./created/")
    parser.add_argument("-i", "--input_dir", default="./tmp/")
    parser.add_argument("-temp", "--temperature")
    parser.add_argument("-r", "--run")

    parser.add_argument("-d", "--dynamic")
    parser.add_argument("-dt", "--dynamic_time")
    parser.add_argument("-f", "--frequency")
    parser.add_argument("-g", "--gamma", default=1)
    parser.add_argument("-ad", "--average_dist")

    parser.add_argument("-rn", "--random_neighbor")

    return parser


def main():
    # argparser
    parser = init_argparse()
    args = parser.parse_args()

    graphs = [f for f in os.listdir("./tmp/")]

    for g in graphs:

        # print(g)
        # name = g[:-8]

        # print(name)

        # Graph
        G: nx.Graph = nx.read_graphml(f"./tmp/{g}")

        G: nx.Graph = nx.relabel_nodes(
            G, lambda n: n[1:] if "n" in n else n
        )  # i graph names nodes n0, n1 etc: remove leading n

        # CONFIG
        config = ConfigParser()

        graphml = "".join(nx.generate_graphml(G))

        config["DEFAULT"] = {"synchronization_model": args.type, "graph": graphml}

        nodes = list(G.nodes)
        for n in nodes:

            narr = []
            for _, neighbor in enumerate(G.neighbors(n)):
                narr.append(str(neighbor))

            config[str(n)] = {
                "node_id": n,
                "synchronization_model": args.type,
                "neighbors": "-".join(narr),
                "time": args.time,
            }

            if args.type == "kuramoto":
                config[str(n)].update(
                    {
                        "c": args.cs,
                        # "frequency": str(np.random.normal(loc=0.01, scale=0.05)),
                        "frequency": args.frequency,
                        "dynamic": args.dynamic,
                    }
                )

                if args.dynamic == "True":
                    config[str(n)].update(
                        {
                            "dynamic_time": args.dynamic_time,
                        }
                    )

            elif args.type == "metropolis":
                config[str(n)].update(
                    {
                        "max_states": args.max_states,
                        "temperature": args.temperature,
                        "random_neighbor": args.random_neighbor,
                    }
                )

            elif args.type == "mypotts":
                config[str(n)].update(
                    {
                        "coupling_strength": args.cs,
                        "max_states": args.max_states,
                        "dynamic": args.dynamic,
                    }
                )

                if args.dynamic == "True":
                    config[str(n)].update(
                        {
                            "gamma": args.gamma,
                            "avg_dist": args.average_dist,
                            "dynamic_time": args.dynamic_time,
                        }
                    )

            elif args.type == "clock":
                config[str(n)].update(
                    {
                        "coupling_strength": args.cs,
                        "max_states": args.max_states,
                        "dynamic": args.dynamic,
                    }
                )

                if args.dynamic == "True":
                    config[str(n)].update(
                        {
                            "gamma": args.gamma,
                            "avg_dist": args.average_dist,
                            "dynamic_time": args.dynamic_time,
                        }
                    )

        with open(
            f"{'./created/'}{args.type}{'_d' if args.dynamic == 'True' else ''}_CS{str(args.cs).replace('.','-')}_{g.replace('.','-')}.ini",
            "w",
        ) as configfile:
            config.write(configfile)


if __name__ == "__main__":
    main()
