import pandas as pd
import asyncio
import json

# import time


background_tasks = set()
file_lock = asyncio.Lock()

big_d = pd.DataFrame()


async def handle_con_task_wrapper(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
):
    global background_tasks

    task = asyncio.create_task(handle_con(reader, writer))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


async def handle_con(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global big_d, file_lock

    data = await reader.read()
    message = data.decode()

    writer.close()
    await writer.wait_closed()

    try:
        msg_dict = json.loads(message)

        new_df = await convert_dict_to_pd(msg_dict["data"])

        new_df["time"] = new_df["time"].astype(float)

        node_id = int(msg_dict["node"])

        async with file_lock:

            try:
                old_df = pd.read_csv(f'{msg_dict["run_id"]}.csv')
                old_df["time"] = old_df["time"].astype(float)

                df = pd.merge(new_df, old_df, on="time", how="outer")
            except FileNotFoundError:
                df = new_df

            df.rename(columns={"values": str(node_id)}, inplace=True)

            df = df.sort_values("time", ascending=True)
            df.to_csv(f'{msg_dict["run_id"]}.csv', index=False)

            print(f"{msg_dict['run_id']}: {len(df.columns)-1}")

    except json.JSONDecodeError:
        print("not json")
        print(message)


async def convert_dict_to_pd(msg_dict: dict):
    w_added_labels = {"time": list(msg_dict.keys()), "values": list(msg_dict.values())}
    return pd.DataFrame.from_dict(data=w_added_labels)


# async def get_node_column_labels(df: pd.DataFrame) -> list:
#     col = list(df.columns)
#     col.remove("time")
#     return col


async def main():
    server = await asyncio.start_server(handle_con_task_wrapper, "0.0.0.0", 50000)

    print("serving")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
