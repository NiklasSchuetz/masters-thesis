from random import randint, randrange
from .interface import SendingMessageError, Synchronisation_Interface
import asyncio
import json
from time import time
from math import sin, pi

start_time: float = 0


class KuramotoModell(Synchronisation_Interface):
    def __init__(self, node):
        self.node = node
        self.frequency: float = 0
        self.time_skew: float = 0
        self.run: str = ""
        self.run_time = 30
        self.C: float = 0.00000001
        self.S: float = 1
        self.dynamic_cs: bool = False
        self.dynamic_time: float = 10

        self.logging: asyncio.Event = asyncio.Event()
        self.flooded_end: bool = False
        self.flooded_lck: asyncio.Lock = asyncio.Lock()
        self.handling_incoming_synchro_lck: asyncio.Lock = asyncio.Lock()

        self.background_tasks = set()  # needed cause asyncio is :(

    def register_new_config(self, msg: dict):
        self.frequency: float = float(msg["frequency"])
        self.time_skew: float = float(randint(0, 500))
        self.log_complete: bool = False
        self.run: str = msg["run"]
        self.run_time: float = float(msg["time"])
        self.flooded_end: bool = False
        self.C = float(msg["c"])
        try:
            self.S: float = float(msg["s"])
        except KeyError:
            pass
        try:
            if msg["dynamic"] == "True":
                self.dynamic_cs: bool = True
                self.dynamic_time: float = float(msg["dynamic_time"])
            else:
                self.dynamic_cs: bool = False
        except KeyError:
            self.dynamic_cs: bool = False

    def get_phase(self) -> float:
        period = 1 / self.frequency
        return (((time() + self.time_skew) % period) * 2 * pi) / (period)

    def get_signal(self) -> float:
        return sin(self.get_phase())

    def update_new_frequency(self, partner_phase: float) -> None:
        global start_time

        cs: float = self.coupling_strength_f2()

        if self.dynamic_cs and time() - start_time > self.dynamic_time:

            period: float = 1 / self.frequency
            phase_diff = self.get_phase() - partner_phase

            dynamic_coupling_strength = cs * (1 - abs(sin(phase_diff)))

            period += dynamic_coupling_strength * (
                sin(phase_diff) / abs(sin(phase_diff))
            )
        else:
            period: float = 1 / self.frequency
            period += cs * sin(self.get_phase() - partner_phase)

        self.frequency = 1 / period

    def coupling_strength_f3(self, neighbor_degree, C: float, S: float):
        return (C + (neighbor_degree / S)) / self.node.degree

    def coupling_strength_f2(self) -> float:
        # global start_time
        # if self.dynamic_cs and time() - start_time < self.dynamic_time:
        #     phase_diff = abs(partner_phase - self.get_phase())
        #     return ((10 - 5 * phase_diff) * self.C) / self.node.degree
        # else:
        return self.C / self.node.degree

    async def log_task(self):
        start = time()

        self.logging.set()
        while self.logging.is_set():
            self.node.history[
                "%.2f" % (time() - start)
            ] = (
                self.get_signal()
            )  # 2 digits after dot https://floating-point-gui.de/languages/python/
            await asyncio.sleep(0.05)

        await asyncio.sleep(10)
        await self.node.send_logs()

    async def handle(self, msg: dict, writer: asyncio.StreamWriter):

        if msg["operation"] == "start":
            await writer.drain()
            writer.close()
            await writer.wait_closed()

            task = asyncio.create_task(self.handle_start_synchronisation())
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)

            # await self.start_synchronisation()
        elif msg["operation"] == "synchro-request":
            _ = await self.handle_incoming_synchro(writer, msg)
        elif msg["operation"] == "end":
            _ = await self.handle_end_synchro(writer, msg)

    async def handle_start_synchronisation(self):
        global start_time

        start_time = time()

        print(f"start synchro: {self.run}")

        task = asyncio.create_task(self.log_task())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

        while time() - start_time < self.run_time:
            await asyncio.sleep(0.1)

            msg = json.dumps(
                {
                    "type": "synchronization",
                    "operation": "synchro-request",
                    "initiator_phase": self.get_phase(),
                    "initiator_id": self.node.id,
                    "degree": self.node.degree,
                }
            )

            try:
                (
                    _,
                    writer,
                    reader,
                ) = await self.node.send_message_to_random_neighbor(msg)

                data = await reader.read(2000)
                res = data.decode()

                writer.close()
                res_dict = json.loads(res)

                self.update_new_frequency(partner_phase=res_dict["response_phase"])
            except SendingMessageError:
                print("synchro step failed")

        self.logging.clear()

        # flood end
        msg: str = json.dumps({"type": "synchronization", "operation": "end"})
        await self.node.send_message_to_all_neighbors(msg)
        self.flooded_end = True

    async def handle_incoming_synchro(
        self, writer: asyncio.StreamWriter, msg: dict
    ) -> None:
        async with self.handling_incoming_synchro_lck:
            response = json.dumps(
                {
                    "type": "synchronization",
                    "operation": "synchro-response",
                    "response_phase": self.get_phase(),
                    "degree": self.node.degree,
                }
            )

            self.update_new_frequency(partner_phase=float(msg["initiator_phase"]))

            writer.write(response.encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()

    async def handle_end_synchro(self, writer: asyncio.StreamWriter, msg: dict) -> None:
        # closing writer
        await writer.drain()
        writer.close()
        await writer.wait_closed()

        # END Logging by clearing event
        async with self.flooded_lck:
            self.logging.clear()
            if self.flooded_end == True:  # return early if alreaddy
                return None

            await self.node.send_message_to_all_neighbors(json.dumps(msg))
            self.flooded_end = True
            return None
