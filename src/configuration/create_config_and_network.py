import os
from time import sleep

import subprocess as sub


def create_network():

    network_type = input(
        "What type of network? Type the number\n\t(1) Popularity\n\t(2) Barabási Albert\n\t(3) Watts Strogatz\n"
    )

    if network_type == "1":
        node_count: int = int(input("n\thow many nodes?\n"))
        edge_count: int = int(input("e\thow many edges?\n"))
        # node_count = 250
        # edge_count = 1250
        community_count: int = int(input("c\thow many communities?\n"))
        ip: str = str(
            input(
                "ip\tWhich percentage do you want to have intra-edges (0 to 100) for range use a-b (eg. 20-80)?\n"
            )
        )
        runs: int = int(input("how many networks do u want per intrapercentage?\n"))

        if "-" in ip:
            num = ip.split("-")
            intra_percents: list = [
                i / 100 for i in range(int(num[0]), int(num[1]) + 1, 5)
            ]  # 5 step distance
        else:
            intra_percents: list = [int(ip) / 100]

        for ipr in intra_percents:
            # for run in range(runs):
            for run in range(35, 50):
                cmd_line = [
                    "python",
                    "popularitynetwork.py",
                    "-n",
                    str(node_count),
                    "-e",
                    str(edge_count),
                    "-c",
                    str(community_count),
                    "-ip",
                    str(ipr),
                    "-o",
                    f"./tmp/pop_N{node_count}_E{edge_count}_C{community_count}_IP{ipr}_{run}",
                ]

                sub.Popen(cmd_line)

        return len(intra_percents) * runs

    elif network_type == "2":
        node_count: int = int(input("n\thow many nodes?\n"))
        edge_count: int = int(input("m\thow many edges per step?\n"))

        pow: str = str(
            input("power\tWhich power do u want? for range use a-b (eg. 2.5-3)?\n")
        )
        runs: int = int(input("how many networks do u want per power?\n"))

        # if "-" in pow:
        #     num: list = pow.split("-")
        #     print(num)
        #     powers: list = [
        #         "%.2f" % i for i in np.arange(float(num[0]), float(num[1]) + 0.1, 0.1)
        #     ]
        # else:
        #     powers: list = [pow]

        if "-" in pow:
            powers = pow.split("-")
        else:
            powers = [pow]

        # call barabasi-albert.r
        # Rscript --vanilla sillyScript.R iris.txt out.txt

        for power in powers:
            for run in range(runs):
                # for run in range(50, 100):
                cmd_line = [
                    r"C:\\Program Files\\R\\R-4.2.1\\bin\\Rscript",
                    "barabasi-albert.r",
                    f"{node_count}",
                    f"{edge_count}",
                    f"{power}",
                    f"tmp/ba_N{node_count}_M{edge_count}_P{str(power).replace('.','-')}_{run}",
                ]

                sub.Popen(cmd_line)

        return len(powers) * runs

    elif network_type == "3":
        node_count: int = int(input("n\thow many nodes?\n"))
        k: int = int(input("k\tmean degree of nodes\n"))
        beta: str = input(
            "p\t beta - possibility of rewiring a edge? for multiple use a-b-c-d-... (eg. 0.0001-0.1-0.2-0.5)?\n"
        )
        runs: int = int(input("how many networks do u want per beta?\n"))

        if "-" in beta:
            betas = beta.split("-")
        else:
            betas = [beta]

        for beta in betas:
            for run in range(runs):
                # for run in range(50, 100):
                cmd_line = [
                    "python",
                    "watts_strogatz.py",
                    "-n",
                    str(node_count),
                    "-k",
                    str(k),
                    "-b",
                    str(beta),
                    "-o",
                    f"./tmp/ws_N{node_count}_k{k}_b{str(beta).replace('.','-')}_{run}",
                ]

                sub.Popen(cmd_line)

        return len(betas) * runs


def create_ini():
    dynamic = False
    synchro_type = input(
        "\n\nWhat type of Synchronization model?\n\t(1) Kuramoto\n\t(2) Potts\n\t(3) Clock\n\t(4) Metropolis"
    )
    time = int(
        input("How long do u want the synchronization process to run? (in seconds): ")
    )

    cmd_line = [
        "python",
        "create_config.py",
        "-ti",
        f"{time}",
    ]

    if synchro_type != 4:

        d: int = int(input("do u want dynamic coupling strength? (1) yes (2) no: "))

        if d == 1:
            dynamic = True

            dt: float = float(input("after how many seconds should dynamic start? "))
            cmd_line.extend(["-d", "True", "-dt", f"{dt}"])

        else:
            cmd_line.extend(["-d", "False"])

    if synchro_type == "1":
        C: float = float(
            input("What value do you want for C (f2 coupling strength)?\n")
        )

        # f: float = float(input("what frequency?\n"))
        f: float = 0.05

        cmd_line.extend(["-t", "kuramoto", "-cs", str(C), "-f", str(f)])

        sub.Popen(cmd_line).wait()

    elif synchro_type == "2":
        max_spins: int = int(input("How many states: "))
        # coupling: float = float(input("What coupling strength do u want? (0-100): \n"))
        coupling: float = 0

        cmd_line.extend(
            [
                "-t",
                "mypotts",
                "-s",
                str(max_spins),
                "-cs",
                str(coupling),
            ]
        )

        if dynamic:
            gamma: int = int(input("which gamma (step size)?: "))
            avg_dist: int = (max_spins // 2) // 2
            cmd_line.extend(
                [
                    "-g",
                    f"{gamma}",
                    "-ad",
                    f"{avg_dist}",
                ]
            )

        sub.Popen(cmd_line).wait()

    elif synchro_type == "3":
        max_spins: int = int(input("How many spins: "))
        # coupling: int = int(input("What coupling strength do u want? (0-100): \n"))

        coupling: float = 0

        cmd_line.extend(
            [
                "-t",
                "clock",
                "-s",
                str(max_spins),
                "-cs",
                str(coupling),
            ]
        )

        if dynamic:
            gamma: int = int(input("which gamma (step size)?: "))
            avg_dist: int = (max_spins // 2) // 2
            cmd_line.extend(
                [
                    "-g",
                    f"{gamma}",
                    "-ad",
                    f"{avg_dist}",
                ]
            )

        sub.Popen(cmd_line).wait()

    elif synchro_type == "4":
        max_spins: int = int(input("How many states: "))
        temp: str = input("temperature: ")
        rn: str = input("use state of random neighbor? (1) yes (2) no: ")

        cmd_line.extend(["-t", "metropolis", "-s", str(max_spins), "-temp", temp])

        if rn == "1":
            cmd_line.extend(["-rn", "True"])
        else:
            cmd_line.extend(["-rn", "False"])

        sub.Popen(cmd_line).wait()


def remove_temp_graphml_files():
    # remove created graphml files from temp
    os.chdir(r"tmp")
    all_files = os.listdir()

    for f in all_files:
        os.remove(f)


if __name__ == "__main__":
    network_count = create_network()

    os.chdir(r"tmp")
    while True:  # count if all networks were created
        sleep(0.1)
        if len(os.listdir()) == network_count:
            break
    os.chdir("..")

    create_ini()
    remove_temp_graphml_files()
