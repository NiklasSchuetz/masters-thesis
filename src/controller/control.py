import json
import os
import asyncio
from configparser import ConfigParser
from random import randint
from time import sleep


def read_files() -> list:
    return [f for f in os.listdir(".") if "_" in f]


async def send_message(message, to):
    _, writer = await asyncio.open_connection(
        f"node-{to}.stsservice.ma-schuetz-dcun.svc.cluster.local", 50000
    )
    writer.write(message.encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def main():
    configparser = ConfigParser()
    conf_files = read_files()

    print(f"found files: {conf_files}")

    while conf_files:
        try:
            conf: str = conf_files.pop()
        except IndexError:
            print("DONE")
            return

        configparser.read(conf)
        run_id = conf[:-4]
        print(f"start: {run_id}")

        print("\tconfig")
        for node_id in configparser.sections():
            node_section = configparser[node_id]

            msg_dict = {
                "type": "node",
                "operation": "config",
                "run": run_id,
            }

            msg_dict.update(
                {k: v for k, v in node_section.items() if k not in ["graph"]}
            )

            await send_message(json.dumps(msg_dict), node_id)

        # Share initial state for metro and potts
        if configparser["0"]["synchronization_model"] in ["mypotts", "metropolis"]:
            sleep(2)
            print("\tshare state")
            for node_id in configparser.sections():
                msg = json.dumps(
                    {"type": "synchronization", "operation": "share_state"}
                )
                await send_message(msg, node_id)
                sleep(0.05)

        # Wait before start
        if configparser["0"]["synchronization_model"] in ["mypotts", "metropolis"]:
            sleep(5)
        else:
            sleep(2)

        # Start
        print("\tstart")
        for node_id in configparser.sections():
            msg = json.dumps({"type": "synchronization", "operation": "start"})
            await send_message(msg, node_id)

        time_for_run = float(configparser["0"]["time"])

        total_wait_time: float = time_for_run + (len(configparser.sections()) / 4.5) + 5
        print(f"\twaiting {total_wait_time} seconds")
        sleep(total_wait_time)


if __name__ == "__main__":
    asyncio.run(main())
    print("All synchronizations are finished!")
