import sys
from typing import Tuple, Dict


sys.path.append("..")

from synchronisation.kuramoto import KuramotoModell
from synchronisation.clock import Clock
from synchronisation.metrohasting import MetroHasting
from synchronisation.bsrg import BSRG
from synchronisation.interface import SendingMessageError, Synchronisation_Interface
import asyncio
from random import choice
import json
from socket import gaierror, gethostbyname


class Node:
    def __init__(self):
        self.id: int = None
        self.neighbors: list[int] = None
        self.synchronization_module: Synchronisation_Interface = None
        self.degree: int = None

        # Dict: timestamp since start  - state/signal
        self.history: Dict[float, float] = {}

        self.background_tasks = (
            set()
        )  # to keep a reference to background tasks, so they do not get garbage collected

        # to store ip locally so no dns call is needed
        # currently not used
        self.local_ip_cache = {}

    def register_synchronisation_modell(self, msg: dict) -> None:
        if msg["synchronization_model"] == "kuramoto":
            self.synchronization_module = KuramotoModell(self)
        elif msg["synchronization_model"] == "clock":
            self.synchronization_module = Clock(self)
        elif msg["synchronization_model"] == "metropolis":
            self.synchronization_module = MetroHasting(self)
        elif msg["synchronization_model"] == "mypotts":
            self.synchronization_module = BSRG(self)

        self.synchronization_module.register_new_config(msg=msg)

    def register_new_node_config(self, msg: dict) -> None:
        self.id = msg["node_id"]
        self.neighbors = [int(id) for id in msg["neighbors"].split("-")]
        self.degree = len(self.neighbors)
        self.history = {}
        self.background_tasks = set()
        self.local_ip_cache = {}
        # self.setup_local_ip_cache()

    def get_neighbors(self) -> list[int]:
        return self.neighbors

    def get_random_neighbor(self) -> int:
        return choice(self.neighbors)

    async def send_logs(self) -> None:
        msg = json.dumps(
            {
                "run_id": self.synchronization_module.run,
                "node": int(self.id),
                "data": self.history,
            }
        )

        while True:
            try:
                writer, _ = await self.send_message_to(
                    msg=msg, to="logstorage", port=50000
                )

                writer.write_eof()
                writer.close()
                await writer.wait_closed()

                print(f"SEND LOGS: {sys.getsizeof(msg)}")
                return
            except SendingMessageError:
                await asyncio.sleep(0.5)

    async def start_server(self):
        server = await asyncio.start_server(self.handle_connection, "0.0.0.0", 50000)

        async with server:
            await server.serve_forever()

    async def send_message_to_local_cache(
        self, msg: str, to_node_id: str = None, port: int = 50000, direct: str = None
    ) -> Tuple[asyncio.StreamWriter, asyncio.StreamReader]:
        """Method to send a message using the local cache

        Use either to_node_id or direct.
        Use direct to provide an ip to send to or to_node_id to use the local cache/DNS to send to node with the given id

        Args:
            msg: the message
            to_node_id: the id of the node one wants to send the message.
            direct: ip of the receipient
            port: port to send to

        Returns:
            asyncio Streamwriter: to write to the TCP connection
            asyncio Streamwreader: to read from the TCP connection


        Raises:
            SendingMessageError

        """

        while True:
            try:
                if direct:
                    reader, writer = await asyncio.open_connection(direct, port)
                else:
                    try:
                        ip = self.local_ip_cache[to_node_id]
                    except KeyError:
                        pass
                    reader, writer = await asyncio.open_connection(ip, port)

                writer.write(msg.encode())
                await writer.drain()
                return writer, reader

            except (TimeoutError, ConnectionResetError, gaierror, OSError) as e:
                # this happens a lot in big networks so we give it an extra option
                if direct == "logstorage":
                    continue

                print(f"{e}: failed sending msg to id: {to_node_id} \n{msg}")
                if e == TimeoutError:
                    self.check_local_ip_cache_entry(to_node_id)
                else:
                    raise SendingMessageError

    async def send_message_to(
        self, msg: str, to: str = None, port: int = 50000
    ) -> Tuple[asyncio.StreamWriter, asyncio.StreamReader]:

        try:
            reader, writer = await asyncio.open_connection(to, port)

            writer.write(msg.encode())
            await writer.drain()
            return writer, reader

        except (TimeoutError, ConnectionResetError, gaierror, OSError):
            raise SendingMessageError

    async def send_message_to_random_neighbor(
        self, msg: str
    ) -> Tuple[int, asyncio.StreamWriter, asyncio.StreamReader]:
        neighborid: int = self.get_random_neighbor()

        to = f"node-{neighborid}.stsservice.ma-schuetz-dcun.svc.cluster.local"
        try:
            writer, reader = await self.send_message_to(msg=msg, to=to)
            return neighborid, writer, reader
        except SendingMessageError:
            raise SendingMessageError

    async def send_message_to_all_neighbors(self, msg: str) -> None:
        for id in self.neighbors:

            to = f"node-{id}.stsservice.ma-schuetz-dcun.svc.cluster.local"
            try:
                writer, _ = await self.send_message_to(msg, to=to)

                await writer.drain()
                writer.close()
                await writer.wait_closed()
            except SendingMessageError:
                raise SendingMessageError

    async def handle_connection_task_wrapper(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """This function gets called when a new TCP connection is created.

        It creates a task with a function to actually handle the connection,
        stores it in a set and adds a callback to remove the task
        from the set when it ends.
        """

        task = asyncio.create_task(self.handle_connection(reader=reader, writer=writer))
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    async def handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Read the message from the TCP connection and call the corresponding functions.

        Messages are json format

        every message has to contain the key "type"!
        if "type" is "node" the message is meant to be handled by the node
        if "type" is "synchronization" the messaged is passed to the "handle" function of the set synchronization module
        """
        data = await reader.read(2000)
        message = data.decode()

        try:
            msg_dict = json.loads(message)

            if msg_dict["type"] == "node":
                if msg_dict["operation"] == "config":
                    self.register_new_node_config(msg_dict)
                    self.register_synchronisation_modell(msg_dict)
            elif (
                msg_dict["type"] == "synchronization"
                and self.synchronization_module is not None
            ):
                try:
                    await self.synchronization_module.handle(
                        msg=msg_dict, writer=writer
                    )
                except AttributeError:
                    print("No synchronization module with handle function!")

        except json.JSONDecodeError:
            print("not json")
            print(f"received: {message}")

    def setup_local_ip_cache(self) -> None:
        # neighbors
        for neighbor_id in self.neighbors:
            ip = self.get_node_ip_by_dns(neighbor_id)
            self.local_ip_cache[neighbor_id] = ip

        # logstorage
        ip = self.get_service_ip_by_dns("logstorage")
        self.local_ip_cache[neighbor_id] = ip

    def check_local_ip_cache_entry(self, id=None, service=None) -> None:
        if id != None:
            ip = self.get_node_ip_by_dns(id)
            self.local_ip_cache[id] = ip
        if service != None:
            ip = self.get_service_ip_by_dns(service)
            self.local_ip_cache[service] = ip

    def get_node_ip_by_dns(self, node_id) -> str:
        return gethostbyname(
            f"node-{node_id}.stsservice.ma-schuetz-dcun.svc.cluster.local"
        )

    def get_service_ip_by_dns(self, service) -> str:
        return gethostbyname(f"{service}")


async def main():
    node = Node()
    await node.start_server()


if __name__ == "__main__":
    print("running main")
    asyncio.run(main())
