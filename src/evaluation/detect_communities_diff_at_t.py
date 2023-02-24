import json
from math import pi
import multiprocessing
import subprocess
from time import time
from scipy.interpolate import InterpolatedUnivariateSpline
import pandas as pd
import numpy as np
import networkx as nx
from configparser import ConfigParser
import signal

from common_methods import (
    read_csvs,
    write_metrics_to_file,
    create_metrics_for_node,
    create_metrics_for_run,
)


def main():
    detection_time = 20

    # create iterable with function args
    arguments = []
    for csv in read_csvs():
        arguments.append((csv, detection_time))

    if len(arguments) == 0:
        print(
            "no csv files found! put csv and ini files in the /evaluation/detect/ folder"
        )
        return

    # ctrl + c to stop children only works correctly on unix system!
    # remove sigint handler -> children inherit sigint handler and can be shutdown by ctrl + c
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    with multiprocessing.Pool(processes=8) as pool:

        signal.signal(signal.SIGINT, original_sigint_handler)  # restore sigint handler

        try:
            res = pool.starmap_async(run_detection, arguments)
            res.get(90000)  # we need timeout for ctrl + c to work
        except KeyboardInterrupt:
            print("Keyboard Interrupt: Terminate")
            pool.terminate()


def run_detection(csv: str, detection_time: float = 20) -> None:
    """
    run_detection runs an community detection and analysis of a single run.

    Args:
        csv: the name of the csv of the run
        detection_time: the time in seconds after the start at which values are compared

    Returns:
        None

    Raises:
        None
    """
    start = time()  # for timing

    cp = ConfigParser()
    config = csv[:-4]

    ini_file = f"{config}.ini"
    res = cp.read(f"./detect/{ini_file}")

    graph: str = cp["DEFAULT"]["graph"]
    G: nx.Graph = nx.parse_graphml(graph)
    G: nx.Graph = nx.relabel_nodes(
        G, lambda n: n[1:] if "n" in n else n
    )  # i graph names nodes n0, n1 etc: remove leading n

    # infos about synchronization
    synchro_type: str = cp["DEFAULT"]["synchronization_model"]
    max_time: float = float(cp["0"]["time"])

    max_states: int = -1
    if synchro_type in ["mypotts", "clock"]:
        max_states: int = int(cp["0"]["max_states"])

    # read and prepare dataframe
    df = pd.read_csv(f"./detect/{csv}")
    df = df.rename(index=lambda x: f"z{x}")
    df = df[df.time <= max_time]

    # community detection
    detection, deviations = detect_communities(
        G=G,
        df=df,
        synchro_type=synchro_type,
        detection_time=detection_time,
        max_states=max_states,
    )

    write_metrics_to_file(detection, f"{config}_nodes", overwrite=False)

    # metrics
    # metrics_nodes = create_metrics_for_node(G, detection)
    # metrics = create_metrics_for_run(metrics_nodes, deviations)

    # write_metrics_to_file(metrics_nodes, f"{config}_nodes", overwrite=False)
    # write_metrics_to_file(metrics, config, overwrite=True)

    print(f"{config} in {time()-start}")


def detect_communities(
    G: nx.Graph,
    df: pd.DataFrame,
    synchro_type: str,
    detection_time: float,
    max_states: int,
) -> tuple[dict, list]:
    """
    detect_communities performs the community detection by comparing the values at time "detection_time"

    Args:
        G: the graph of the network, used to get the neighbors of nodes
        df: a dataframe containing a collumn time with time stamps and collumns for every node
        synchro_type: the used synchronization module, e.g. kuramoto, metropolis
        detection_time: the time after start of the synchronization at which values are compared
        max_states: not used if synchro_type is "kuramoto". gives the number of states

    Returns:
        detection results: a dict containing the source nodes as keys and a nested dict as values.
            format of dection results:
            {
                "1": {
                    "deviation_1":{
                        "in": ["2","3"],
                        "out": ["4","5"]
                    },
                    "deviation_2":{
                        "in": ["2","3","4"],
                        "out": ["5"]
                    },
                    ...
                }
                "2": {...}
            }
        deviations: list containing the used deviations
    """

    interpolated: dict = {}

    for node in G.nodes:  # interpolate
        node: str = str(node)

        try:
            d: dict = {"time": df["time"], node: df[node]}
            df_node: pd.DataFrame = pd.DataFrame.from_dict(d)
            df_node = df_node.dropna()

            vals = np.absolute(df_node[f"{node}"])

            interpolated[node] = InterpolatedUnivariateSpline(x=df_node["time"], y=vals)
        except KeyError:
            print(f"node {node} not found")

    detection_results = {}
    deviations = []
    # iterate over all nodes -> iterate over all neighbors
    # -> compare if value difference is in deviation -> decide if in community
    for source_node in G.nodes:
        try:
            source_node: str = str(source_node)
            detection_results[source_node] = {}

            t_source = interpolated[source_node](detection_time)

            max_diff: float = 0
            start: float = 0
            step: float = 0
            if synchro_type == "kuramoto":
                max_diff = 2
                start = 0.1
                step = 0.1
            elif synchro_type in ["mypotts", "metropolis", "clock"]:
                max_diff = max_states // 2
                start = max_diff * 0.05
                step = max_diff * 0.05

            deviations = []
            for deviation in np.arange(start, max_diff, step):
                deviation = float("%.2f" % deviation)  # remove floating point error
                deviations.append(deviation)
                detection_results[source_node][deviation] = {"in": [], "out": []}

                for target_node in G.neighbors(source_node):
                    target_node: str = str(target_node)

                    t_target = interpolated[target_node](detection_time)

                    diff = abs(t_target - t_source)

                    if diff > max_diff:  # wrap around
                        diff = max_states - diff

                    if diff <= deviation:
                        detection_results[source_node][deviation]["in"].append(
                            target_node
                        )
                    else:
                        detection_results[source_node][deviation]["out"].append(
                            target_node
                        )

        except KeyError:
            exit()

    return detection_results, deviations


if __name__ == "__main__":
    main()
