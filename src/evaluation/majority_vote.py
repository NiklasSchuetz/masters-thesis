from configparser import ConfigParser
import multiprocessing
import os
import json
import signal
import networkx as nx
from common_methods import (
    read_csvs,
    write_metrics_to_file,
    create_metrics_for_node,
    create_metrics_for_run,
)


# This reads in the node metrics and performs majority vote on dem before creating node metrics.


def main():

    files = [f for f in os.listdir("./gen/") if "nodes" in f]

    configs = set(("_".join(f.split("_")[:-2]) for f in files))

    args = []
    for cfg in configs:
        args.append((cfg, 0))

    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    with multiprocessing.Pool(processes=10) as pool:

        signal.signal(signal.SIGINT, original_sigint_handler)  # restore sigint handler

        try:
            res = pool.starmap_async(majority_vote, args)
            res.get(90000)  # we need timeout for ctrl + c to work
        except KeyboardInterrupt:
            print("Keyboard Interrupt: Terminate")
            pool.terminate()


def majority_vote(cfg, _):
    # read nodes of config
    ini = [f for f in os.listdir("./detect/") if cfg in f and "ini" in f][0]

    cp = ConfigParser()
    res = cp.read(f"./detect/{ini}")

    graph: str = cp["DEFAULT"]["graph"]
    G: nx.Graph = nx.parse_graphml(graph)
    G: nx.Graph = nx.relabel_nodes(G, lambda n: n[1:] if "n" in n else n)

    detections = [f for f in os.listdir("./gen/") if cfg in f]
    runs = []
    for d in detections:
        with open(f"./gen/{d}") as f:
            runs.append(json.load(f))

    nr_of_runs = len(runs)

    run1 = runs.pop(0)

    result = {}
    for node, dev_dict in run1.items():
        node = str(node)
        result[node] = {}
        for dev, inout_dict in dev_dict.items():
            dev = str(dev)
            try:
                result[node][dev] = {"in": [], "out": []}
                for target in inout_dict["in"]:
                    target = str(target)
                    count_in = 0
                    try:
                        for run in runs:
                            if target in run[node][dev]["in"]:
                                count_in += 1
                    except KeyError:
                        pass

                    if count_in > 0:
                        result[node][dev]["in"].append(target)
                    else:
                        result[node][dev]["out"].append(target)
            except TypeError:
                pass

            try:
                for target in inout_dict["out"]:
                    count_out = 0
                    try:
                        for run in runs:
                            if target in run[node][dev]["out"]:
                                count_out += 1
                    except KeyError:
                        pass

                    if count_out > 0:
                        result[node][dev]["out"].append(target)
                    else:
                        result[node][dev]["in"].append(target)
            except TypeError:
                pass
    try:
        deviations = list(result[list(result.keys())[0]].keys())
        node_res = create_metrics_for_node(G=G, detection_results=result)
        run_res = create_metrics_for_run(node_res, deviations)

        write_metrics_to_file(run_res, f"{cfg}")
    except (KeyError, TypeError):
        pass


if __name__ == "__main__":
    main()
