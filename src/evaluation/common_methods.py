import os, json
from statistics import mean
from typing import Dict, Tuple
import networkx as nx
import networkx.algorithms.community as nx_comm


def read_csvs():
    return [f for f in os.listdir("./detect/") if ".csv" in f]


def write_metrics_to_file(metrics: dict, config: str, overwrite: bool = False) -> None:
    try:
        with open(f"./gen/{config}.json", "x") as file:
            file.write(json.dumps(metrics, indent=4))
    except FileExistsError:
        if overwrite:
            with open(f"./gen/{config}.json", "w") as file:
                file.write(json.dumps(metrics, indent=4))


def create_metrics_for_node(G: nx.Graph, detection_results: dict) -> dict:
    """
    create metrics for a single node based on the communities detected by the Louvain Method

    Args:
        G:                  the graph of the network, used to get the neighbors of nodes
        detection_results:  a dict containing the results of the community detection.
                            For format see "detect_communities()"

    Returns:

        deviations: a list containing the used deviations
        metrics:    a dict containg the metrics for each node
                    Format:
                    {
                        "1": {
                            "deviation_1":{
                                "detection_rate": 0.1,
                                "precision": 0.2,
                                "recall": 0.3,
                            },
                            "deviation_2":{
                                "detection_rate": 0.1,
                                "precision": 0.2,
                                "recall": 0.3,
                            },
                            ...
                        }
                        "2": {...}
                    }
    """

    # Compare with GRAPH:
    louvain_communities = list(nx_comm.louvain_communities(G, seed=123))
    count_detections: dict = (
        {}
    )  # for storing how many nodes where classified (in-)correctly for each targetnode and deviation
    for louvain_community in louvain_communities:  # over all detected communities
        for (
            source_node
        ) in louvain_community:  # iterate over each node in louvain community
            try:
                count_detections[source_node] = {
                    # all nodes of the louvain community - the node itself
                    "must_in": len(
                        [
                            tn
                            for tn in list(G.neighbors(source_node))
                            if tn in louvain_community
                        ]
                    ),
                    # all nodes which are neighbors but not in community
                    "must_out": len(
                        [
                            tn
                            for tn in list(G.neighbors(source_node))
                            if tn not in louvain_community
                        ]
                    ),
                }
                source_node_results = detection_results[source_node]

                # for deviation: count how many are right and wrong
                for deviation in source_node_results:
                    count_detections[source_node][deviation] = {
                        "correct_in": 0,
                        "incorrect_in": 0,
                        "correct_out": 0,
                        "incorrect_out": 0,
                    }
                    for target_node in detection_results[source_node][deviation]["in"]:

                        if target_node in louvain_community:
                            count_detections[source_node][deviation]["correct_in"] += 1
                        else:
                            count_detections[source_node][deviation][
                                "incorrect_in"
                            ] += 1
                    for target_node in detection_results[source_node][deviation]["out"]:
                        if target_node not in louvain_community:
                            count_detections[source_node][deviation]["correct_out"] += 1
                        else:
                            count_detections[source_node][deviation][
                                "incorrect_out"
                            ] += 1
            except KeyError:
                pass

    metrics = {}
    for source_node in G.nodes:
        source_node = str(source_node)
        try:
            metrics[source_node] = {}
            deviations = [
                dev
                for dev in count_detections[source_node]
                if dev not in ["must_in", "must_out"]
            ]
            for deviation in deviations:
                # Calculate Detection Rates, Precision, Recall

                successfull_detections = (
                    count_detections[source_node][deviation]["correct_out"]
                    + count_detections[source_node][deviation]["correct_in"]
                )
                all_detections = sum(count_detections[source_node][deviation].values())

                detection_rate = successfull_detections / all_detections

                try:
                    precision = count_detections[source_node][deviation][
                        "correct_in"
                    ] / (
                        count_detections[source_node][deviation]["correct_in"]
                        + count_detections[source_node][deviation]["correct_out"]
                    )
                except ZeroDivisionError:
                    precision = 0
                try:
                    recall = count_detections[source_node][deviation]["correct_in"] / (
                        count_detections[source_node][deviation]["correct_in"]
                        + count_detections[source_node][deviation]["incorrect_in"]
                    )
                except ZeroDivisionError:
                    if count_detections[source_node]["must_in"] == 0:
                        recall = 1
                    else:
                        recall = 0
                metrics[source_node][deviation] = {
                    "detection_rate": detection_rate,
                    "precision": precision,
                    "recall": recall,
                }
        except KeyError:
            pass

    return metrics


def create_metrics_for_run(
    node_metrics: dict, deviations: list
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    create metrics for the network based on the metrics of single nodes.

    Args:
        node_metrics:   a dict containg the metrics for each node. for format see "create_metrics_for_node()"
        deviations:     a list containing the used deviations


    Returns:
        run_metrics:    a dict containg the metrics for the whole run
                    Format:
                    {
                        "detection_rate": {
                            "deviation_1": 0.1,
                            "deviation_2": 0.2,
                            ...
                        },
                        "precision": {
                            "deviation_1": 0.1,
                            "deviation_2": 0.2,
                            ...
                        },
                        "recall": {
                            "deviation_1": 0.1,
                            "deviation_2": 0.2,
                            ...
                        }
                    }
    """

    # empty dict to fill later
    run_metrics = {
        "detection_rate": {},
        "precision": {},
        "recall": {},
    }

    for deviation in deviations:
        detection_rates = []
        precision = []
        recall = []

        for node in node_metrics.keys():
            detection_rates.append(node_metrics[node][deviation]["detection_rate"])
            precision.append(node_metrics[node][deviation]["precision"])
            recall.append(node_metrics[node][deviation]["recall"])

        run_metrics["detection_rate"][deviation] = mean(detection_rates)
        run_metrics["precision"][deviation] = mean(precision)
        run_metrics["recall"][deviation] = mean(recall)

    return run_metrics
