import multiprocessing
from statistics import mean
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

# seconds when to start and when to end


def main():
    begin: int = 5
    end: int = 40
    net_AUC: bool = False
    from_source: bool = True
    mutual_membership: bool = False

    # create iterable with function args
    arguments = []
    for csv in read_csvs():
        arguments.append((csv, begin, end, net_AUC, from_source, mutual_membership))

    if len(arguments) == 0:
        print(
            "no csv files found! put csv and ini files in the /evaluation/detect/ folder"
        )
        return

    # ctrl + c to stop children only works correctly on unix system!
    # remove sigint handler -> children inherit sigint handler and can be shutdown by ctrl + c
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    with multiprocessing.Pool(processes=10) as pool:

        signal.signal(signal.SIGINT, original_sigint_handler)  # restore sigint handler

        try:
            res = pool.starmap_async(run_detection, arguments)
            res.get(90000)  # we need timeout for ctrl + c to work
        except KeyboardInterrupt:
            print("Keyboard Interrupt: Terminate")
            pool.terminate()


def run_detection(
    csv: str,
    begin: int = 3,
    end: int = 15,
    net_AUC: bool = False,
    from_source: bool = True,
    mutual_membership: bool = False,
):

    cp = ConfigParser()
    config = csv[:-4]
    start = time()

    df = pd.read_csv(f"./detect/{csv}")
    ini_file = f"{config}.ini"
    res = cp.read(f"./detect/{ini_file}")

    graph: str = cp["DEFAULT"]["graph"]
    synchro_type: str = cp["DEFAULT"]["synchronization_model"]
    max_time: float = float(cp["0"]["time"])

    max_states = -1
    if synchro_type in ["mypotts", "clock"]:
        max_states: int = int(cp["0"]["max_states"])

    G: nx.Graph = nx.parse_graphml(graph)

    G: nx.Graph = nx.relabel_nodes(
        G, lambda n: n[1:] if "n" in n else n
    )  # i graph names nodes n0, n1 etc: remove leading n

    df = df.rename(index=lambda x: f"z{x}")
    df = df[df.time <= max_time]

    if from_source:
        aucs_source = calculate_AUCs_from_sourcenode(
            G, df, begin, end, synchro_type, max_states, net_AUC
        )
        detection, deviations = detect_communities_from_sourcenode(G, aucs_source)
    else:
        aucs = calculate_AUCs(G, df, begin, end, net_AUC)
        detection, deviations = detect_communities(G, aucs)

    write_metrics_to_file(
        detection,
        f"{config}_nodes",
    )

    if mutual_membership:
        for _ in range(10):
            mutual_communitymembership(detection)

    # metrics
    # metrics_nodes = create_metrics_for_node(G, detection)
    # metrics = create_metrics_for_run(metrics_nodes, deviations)

    # write_metrics_to_file(metrics_nodes, config, True, overwrite=False)
    # write_metrics_to_file(metrics, config, overwrite=True)

    # print(json.dumps(metrics, indent=4))

    print(f"{config} in {time()-start}")


def calculate_AUCs(
    G: nx.Graph, df: pd.DataFrame, begin: int, end: int, calculate_net: bool
):
    """calculate total AUCs and net AUCs (integral)"""
    # Calculate AUC for everynode s
    AUCs: dict = {}
    for node in G.nodes:  # interpolieren
        node: str = str(node)

        try:
            d: dict = {"time": df["time"], node: df[node]}
            df_node: pd.DataFrame = pd.DataFrame.from_dict(d)
            df_node = df_node.dropna()

            if calculate_net:
                vals = df_node[f"{node}"]
            else:
                vals = np.absolute(df_node[f"{node}"])  # AUC not integral

            AUCs[node] = InterpolatedUnivariateSpline(
                x=df_node["time"], y=vals
            ).integral(begin, end)
        except KeyError:
            print("node not found")
    return AUCs


def calculate_AUCs_from_sourcenode(
    G: nx.Graph,
    df: pd.DataFrame,
    begin: int,
    end: int,
    synchro_type: str,
    max_states: int,
    calculate_net: bool = False,
):
    """Calculates AUCs (total and net) of the signal difference between source and target nodes"""

    interpolated: dict = {}

    for node in G.nodes:  # interpolieren
        node: str = str(node)

        try:
            d: dict = {"time": df["time"], node: df[node]}
            df_node: pd.DataFrame = pd.DataFrame.from_dict(d)
            df_node = df_node.dropna()

            if calculate_net:
                vals = df_node[f"{node}"]
            else:
                vals = np.absolute(df_node[f"{node}"])  # AUC not integral

            interpolated[node] = InterpolatedUnivariateSpline(x=df_node["time"], y=vals)
        except KeyError:
            print(f"node {node} not found")

    steps_per_second = 15
    time = np.linspace(begin, end, num=((end - begin) * steps_per_second))

    AUCs: dict = {}  # nested dict: {source_node : { target_node : auc}}
    for source_node in G.nodes:
        try:
            source_node: str = str(source_node)

            AUCs[source_node] = {}
            diff = []
            for neighbor in G.neighbors(source_node):

                if synchro_type == "kuramoto":
                    diff = [
                        interpolated[neighbor](t) - interpolated[source_node](t)
                        for t in time
                    ]
                elif synchro_type in ["mypotts", "clock", "metropolis"]:
                    diff = []
                    for t in time:
                        target = interpolated[neighbor](t)
                        node = interpolated[source_node](t)
                        if abs(target - node) < max_states / 2:
                            diff.append((target - node))
                        else:
                            diff.append(max_states - int(node) - target)

                    if not calculate_net:
                        diff = [abs(d) for d in diff]

                AUCs[source_node][neighbor] = InterpolatedUnivariateSpline(
                    x=time, y=diff
                ).integral(begin, end)

                # plt.plot(time, diff)
                # plt.show()
        except KeyError:
            pass

    return AUCs


def detect_communities(G: nx.Graph, AUCs: dict):
    detection_results: dict = {}  # knoten: (detection_abweichung: (status: []))
    deviations = []
    for node in G.nodes:
        try:
            detection_results[node] = {}
            # neighbor_aucs: dict = {n: AUCs[n] for n in G.neighbors(node)}

            neighbor_aucs: dict = {}
            for n in G.neighbors(node):
                try:
                    neighbor_aucs[n] = AUCs[n]
                except KeyError:
                    pass

            # calculate AUC_mean
            auc_mean: float = sum(list(neighbor_aucs.values())) / len(
                list(neighbor_aucs.values())
            )

            # check if same community
            deviations = []
            for detection_abweichung in np.arange(0.1, 0.91, 0.1):
                detection_abweichung = float(
                    "%.2f" % detection_abweichung
                )  # remove floating point error

                deviations.append(detection_abweichung)

                detection_results[node][detection_abweichung] = {"in": [], "out": []}
                # node y is in if: |A_mean − A_y| ≤ 0.1 ∗ A_mean

                for neighbor, auc in neighbor_aucs.items():
                    # print(f"{neighbor}: {auc}")

                    diff: float = abs(auc_mean - auc)
                    # print(f"diff: {diff}")
                    # print(f"should be in: {detection_abweichung * auc_mean}")

                    # abs around
                    if abs(auc_mean - auc) <= detection_abweichung * auc_mean:
                        detection_results[node][detection_abweichung]["in"].append(
                            neighbor
                        )
                    else:
                        detection_results[node][detection_abweichung]["out"].append(
                            neighbor
                        )
        except KeyError:
            pass

    return detection_results, deviations


def detect_communities_from_sourcenode(G: nx.Graph, Aucs: dict) -> tuple[dict, list]:
    detection_results = {}
    deviations: list = []

    for source_node in Aucs:
        detection_results[source_node] = {}
        aucs = list(Aucs[source_node].values())

        mean_auc = mean(aucs)

        # check if same community
        deviations = []

        for detection_abweichung in np.arange(0.1, 0.91, 0.1):
            detection_abweichung = float(
                "%.2f" % detection_abweichung
            )  # remove floating point error

            deviations.append(detection_abweichung)

            detection_results[source_node][detection_abweichung] = {"in": [], "out": []}
            # node y is in if: |A_mean − A_y| ≤ 0.1 ∗ A_mean

            for neighbor, auc in Aucs[source_node].items():
                # print(
                #     f"{auc}: {abs(mean_auc - auc)} < {detection_abweichung * mean_auc}"
                # )
                if abs(mean_auc - auc) <= detection_abweichung * mean_auc:
                    detection_results[source_node][detection_abweichung]["in"].append(
                        neighbor
                    )
                else:
                    detection_results[source_node][detection_abweichung]["out"].append(
                        neighbor
                    )

    return detection_results, deviations


def mutual_communitymembership(detections: dict):
    for deviation in detections["0"].keys():
        for source in detections.keys():
            s_in = detections[source][deviation]["in"]

            for target in s_in:
                if source not in detections[target][deviation]["in"]:

                    in_com = 0
                    not_in_com = 0

                    detected_as_community = list(
                        set(detections[target][deviation]["in"]).intersection(
                            detections[source][deviation]["in"]
                        )
                    )

                    for possible_community_node in detected_as_community:
                        if (
                            target
                            in detections[possible_community_node][deviation]["in"]
                        ):
                            in_com += 1
                        elif (
                            target
                            in detections[possible_community_node][deviation]["out"]
                        ):
                            not_in_com += 1

                    if in_com > not_in_com:
                        detections[target][deviation]["in"].append(
                            source
                        )  # add to community

                    else:
                        detections[source][deviation]["in"].remove(target)
                        detections[source][deviation]["out"].append(target)

        break

    return


if __name__ == "__main__":
    main()
