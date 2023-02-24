import os
import networkx as nx
import networkx.algorithms.community as nx_comm
from scipy.interpolate import InterpolatedUnivariateSpline
import pandas as pd
from configparser import ConfigParser
import matplotlib.pyplot as plt

cp = ConfigParser()
csvs = [f for f in os.listdir("./in/") if ".csv" in f]


for csv in csvs:

    config = csv[:-4]
    print(config)

    df = pd.read_csv(f"./in/{csv}")
    ini_file = f"{config}.ini"
    cp.read(f"./in/{ini_file}")

    graph = cp["DEFAULT"]["graph"]
    type = cp["DEFAULT"]["synchronization_model"]
    max_time: float = float(cp["0"]["time"])

    G: nx.Graph = nx.parse_graphml(graph)
    # G: nx.Graph = nx.read_graphml(f"./in/{config}.graphml")

    G: nx.Graph = nx.relabel_nodes(
        G, lambda n: n[1:] if "n" in n else n
    )  # i graph names nodes n0, n1 etc: remove leading n

    df = df.rename(index=lambda x: f"z{x}")
    df = df[df.time <= max_time]

    interpolations: dict = {}
    for node in G.nodes:  # interpolieren

        try:
            node: str = str(node)

            d: dict = {"time": df["time"], node: df[node]}
            df_node: pd.DataFrame = pd.DataFrame.from_dict(d)
            df_node = df_node.dropna()

            # pos = [abs(v) for v in df_node[f"{node}"]]

            # interpolations[node] = InterpolatedUnivariateSpline(
            #     x=df_node["time"], y=df_node[f"{node}"]
            # )

            plot = plt.plot(df_node["time"], df_node[f"{node}"])
            plt.xlabel("time (s)")
            plt.ylabel("value")

        except KeyError:
            print("KEYERROR")
            print(node)
            continue

    plt.show()

    # coms = nx_comm.louvain_communities(G)
    # print(coms)
    # for node in G.nodes:
    #     node: str = str(node)

    #     print(f"\n{node}")
    #     node_com = []
    #     for com in coms:
    #         if node in com:
    #             node_com = com

    #     d: dict = {"time": df["time"], node: df[node]}
    #     df_node: pd.DataFrame = pd.DataFrame.from_dict(d)
    #     df_node = df_node.dropna()

    #     plt.plot(df_node["time"], df_node[f"{node}"], color="black", marker="o")
    #     print(list(G.neighbors(node)))
    #     for ng in G.neighbors(node):
    #         ng: str = str(ng)

    #         d: dict = {"time": df["time"], ng: df[ng]}
    #         df_node: pd.DataFrame = pd.DataFrame.from_dict(d)
    #         df_node = df_node.dropna()

    #         if ng in node_com:
    #             colr = "green"
    #         else:
    #             colr = "red"

    #         plt.plot(df_node["time"], df_node[f"{ng}"], color=colr)
    #         plt.xlabel("time (s)")
    #         plt.ylabel("value")

    #     plt.show()
