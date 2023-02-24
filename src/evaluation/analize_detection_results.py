# AUFGABEN

# einlesen der jsons aus ./gen/
# zusammen mappen der einzelnen runs: durchschnitt bilden
# graphen erzeugen: scatter plot


# detect communities erzeugt für jede csv (+ini) eine json datei mit den ergebnissen (community detection, recall, precision etc)
# analize.py fasst diese alle zusammen in eine json datei pro netzwerk (alle runs zu einem), speichert und erzeugt contourplots

from collections import defaultdict
import json
from statistics import mean
import pandas as pd
import os


def main():
    generated_files = [f for f in os.listdir("./gen/") if "_nodes" not in f]

    net_syn_configurations = list(
        {"_".join(f.split("_")[:-1]) for f in generated_files}
    )

    synchronization_type = net_syn_configurations[0].split("_")[0]
    network_model = net_syn_configurations[0].split("_")[2]

    dfs = {}

    for config in net_syn_configurations:
        dfs[config] = create_df_for_configuration(config)

    output_dict = {}

    configuration = ""
    for configuration, configuration_df in dfs.items():
        # print(configuration)
        # print(configuration_df)
        # print(" \n")
        output_dict[configuration] = configuration_df.to_dict()

    # output_name = "_".join(configuration.split("_")[:-1])
    with open(f"./results/{synchronization_type}.json", "x") as file:
        file.write(json.dumps(output_dict, indent=4))


def create_df_for_configuration(config: str):
    gen_files = [f for f in os.listdir("./gen/") if "_nodes" not in f]
    runs = [r for r in gen_files if f"{config}_" in r]
    collected = {
        "detection_rate": defaultdict(list),
        "precision": defaultdict(list),
        "recall": defaultdict(list),
    }

    for run in runs:  # über alle runs mit gleicher config
        with open(f"./gen/{run}") as f:
            run_dict = json.load(f)
        for metric, deviation_dict in run_dict.items():
            for deviation, value in deviation_dict.items():
                collected[metric][deviation].append(value)

        # print(json.dumps(collected, indent=2))

    # create df with deviations in a column
    df = pd.DataFrame({"deviations": collected["detection_rate"].keys()})

    for metric, deviation_dict in collected.items():
        # pro metrik neues dict
        sammeln = {}
        for d, v in deviation_dict.items():
            # dict = {k: mean(v) for k, v in v.items()}
            # d deviation
            # v liste mit werten
            sammeln[d] = float("%.4f" % mean(v))

        df[metric] = df["deviations"].map(sammeln)

    return df


if __name__ == "__main__":
    main()
