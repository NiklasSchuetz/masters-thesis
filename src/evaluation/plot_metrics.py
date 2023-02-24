import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json
import os

results = [f for f in os.listdir("./results/")]

networkmap = {
    "pop": "Popularity",
    "ba": "Barabási-Albert",
    "ws": "Watts-Strogatz",
}

synchromap = {
    "kuramoto": "Kuramoto",
    "clock": "pair Potts",
    "mypotts": "multiple Potts",
    "metropolis": "Metropolis",
}

font = {"weight": "normal", "size": 19}

plt.rc("font", **font)


for res in results:
    try:
        with open(f"./results/{res}") as f:
            input: dict = json.load(f)
    except KeyError:
        print("no input results")
        exit()

    fig = plt.figure()

    fig.subplots_adjust(hspace=0.25, left=0.05, right=0.95)

    # Format pyramid
    # detectionrate_format = 211
    # precision_format = 223
    # recall_format = 224

    # Format one line
    detectionrate_format = 131
    precision_format = 132
    recall_format = 133

    detectionrate = fig.add_subplot(detectionrate_format)
    detectionrate.set_title("Accuracy")
    detectionrate.set_ylabel("accuracy")
    detectionrate.set_ylim(0, 1)
    detectionrate.set_box_aspect(1)

    precision = fig.add_subplot(precision_format)
    precision.set_title("Precision")
    precision.set_ylabel("precision")
    precision.set_ylim(0, 1)
    precision.set_box_aspect(1)

    recall = fig.add_subplot(recall_format)
    recall.set_title("Recall")
    recall.set_ylabel("recall")
    recall.set_ylim(0, 1)

    recall.set_box_aspect(1)

    for pos, (ID, value) in enumerate(input.items()):

        df: pd.DataFrame = pd.DataFrame.from_dict(value)
        synchro_type: str = ID.split("_")[0]
        if ID.split("_")[1] == "d":
            network_type: str = ID.split("_")[3]
        else:
            network_type: str = ID.split("_")[2]

        network_identifier: str = ID.split("_")[-1].replace("-", ".")

        if network_type == "pop":
            network_identifier = network_identifier[2:]
        else:
            network_identifier = network_identifier[1:]

        if synchro_type == "kuramoto":
            detectionrate.set_xlabel("signal deviation")
            recall.set_xlabel("signal deviation")
            precision.set_xlabel("signal deviation")
        else:
            detectionrate.set_xlabel("spin deviation")
            recall.set_xlabel("spin deviation")
            precision.set_xlabel("spin deviation")

        # fig.suptitle(f"{synchromap[synchro_type]}: {networkmap[network_type]}")

        # x_tickrange = np.arange(start, end, 3)

        oben = False

        if oben:
            bbox = (0.5, 0.9)
        else:
            bbox = (0.5, 0.25)

        detectionrate.plot(df.deviations, df.detection_rate, label=network_identifier)
        start, end = detectionrate.get_xlim()
        x_tickrange = range(int(start), int(end), 3)  # 3 or 5
        detectionrate.set_xticks(x_tickrange)
        detectionrate.legend(
            loc="upper center", bbox_to_anchor=bbox, ncol=3, prop={"size": 16}
        )

        precision.plot(df.deviations, df.precision, label=network_identifier)
        start, end = precision.get_xlim()
        precision.set_xticks(x_tickrange)
        precision.legend(
            loc="upper center", bbox_to_anchor=bbox, ncol=3, prop={"size": 16}
        )

        recall.plot(df.deviations, df.recall, label=network_identifier)
        start, end = recall.get_xlim()
        recall.set_xticks(x_tickrange)
        recall.legend(
            loc="upper center", bbox_to_anchor=bbox, ncol=3, prop={"size": 16}
        )

plt.show()
