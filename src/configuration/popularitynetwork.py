import networkx as nx
import argparse
from math import ceil
import random

# import networkx.algorithms.community as nx_comm


class NetworkCreationError(RuntimeError):
    pass


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION] ...",
        description="create a graphml file with the specified nodes, edges, clusters, inter-/intra-edges",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"{parser.prog} version 1.0.0"
    )
    parser.add_argument("-n", "--nodes", required=True)
    parser.add_argument("-e", "--edges", required=True)
    parser.add_argument("-c", "--communities", required=True)
    parser.add_argument("-ip", "--intraedgespercent", required=True)
    parser.add_argument("-o", "--output", required=True)

    return parser


def main() -> None:
    parser = init_argparse()
    args = parser.parse_args()

    nodes = int(args.nodes)
    community_count = int(args.communities)
    edges = int(args.edges)
    intra_edges = int(edges * float(args.intraedgespercent))

    inter_edges = edges - intra_edges

    nodes_list = [i for i in range(0, nodes)]

    communities = []
    community_size = ceil(nodes / community_count)

    for i in range(0, nodes, community_size):
        communities.append(nodes_list[i : i + community_size])

    edges_per_community = intra_edges // community_count
    possible_more_intra_edges = intra_edges - community_count * edges_per_community

    # check if graph is possible
    if ((community_size * (community_size - 1)) / 2) < edges_per_community:
        raise (
            NetworkCreationError(
                f"each community has {edges_per_community} edges, but {((community_size * (community_size - 1)) / 2)} are possible"
            )
        )

    # FOR DEBUGGING
    # print(f"nodes {nodes}")
    # print(f"edges {edges}")
    # print(f"community_count {community_count}")
    # print(f"intra_edges {intra_edges}")
    # print(f"inter_edges {inter_edges}")
    # print(f"community_size {community_size}")

    # GENERATION
    # 1. add edges in each community
    # 2. if additional intra community edges exist add them randomly in a community
    # 3. add edges between communities
    tries = 0
    while tries < 100:

        edges_list = []

        for community in communities:
            community_edge_list = []
            for n in community[1:]:
                community_edge_list.append((random.choice(range(community[0], n)), n))

            while len(community_edge_list) < edges_per_community:

                while True:
                    node1, node2 = random.sample(community, k=2)

                    if node1 < node2:
                        node_tuple = (node1, node2)
                    else:
                        node_tuple = (node2, node1)

                    if node_tuple not in community_edge_list:
                        community_edge_list.append(node_tuple)
                        break

            edges_list.extend(community_edge_list)

        remaining_intra = possible_more_intra_edges
        while remaining_intra > 0:
            while True:
                c = random.choice(communities)
                node1, node2 = random.sample(c, k=2)

                if node1 < node2:
                    node_tuple = (node1, node2)
                else:
                    node_tuple = (node2, node1)

                if node_tuple not in edges_list:
                    edges_list.append(node_tuple)
                    break

                remaining_intra -= 1

        # INTER EDGES
        for i in range(inter_edges):
            while True:
                c1, c2 = random.sample(communities, k=2)

                node1 = random.choice(c1)
                node2 = random.choice(c2)

                if node1 < node2:
                    node_tuple = (node1, node2)
                else:
                    node_tuple = (node2, node1)

                if node_tuple not in edges_list:
                    edges_list.append(node_tuple)
                    break

        network = nx.Graph()
        network.add_nodes_from(nodes_list)
        network.add_edges_from(edges_list)

        if nx.is_connected(network):

            import matplotlib.pyplot as plt

            # pos = nx.nx_agraph.graphviz_layout(network, prog="twopi", args="")

            # plt.figure(figsize=(8, 8))
            # nx.draw(
            #     network,
            #     pos,
            #     node_size=20,
            #     alpha=0.5,
            #     node_color="blue",
            #     with_labels=False,
            # )
            # plt.axis("equal")
            # plt.show()

            nx.write_graphml_lxml(network, f"{args.output}")
            return

        tries += 1

    raise (NetworkCreationError(f"Did not create a connected graph in 100 tries"))


if __name__ == "__main__":
    main()
