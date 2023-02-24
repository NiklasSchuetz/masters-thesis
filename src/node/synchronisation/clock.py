from socket import gaierror
from statistics import mean
from time import time
from .interface import Synchronisation_Interface, SendingMessageError
import asyncio
from random import randint
from math import atan2, cos, pi, sin
import json


start_time: float = 0


class Clock(Synchronisation_Interface):
    def __init__(self, node) -> None:
        super().__init__()
        self.node = node
        self.max_states: int = -1
        self.state: int = -1
        # self.coupling_strength: int = None

        self.dynamic_cs: bool = False
        self.gamma: int = 1
        self.avg_dist: int = 100
        self.dynamic_time: float = 10

        self.state_radiant_map: dict = {}

        self.run: str = ""
        self.run_time: float = 30

        self.background_tasks = set()

        self.logging = asyncio.Event()
        self.flooded_end = False
        self.flooded_lck = asyncio.Lock()

    def register_new_config(self, msg: dict) -> None:
        self.run = msg["run"]
        self.run_time = float(msg["time"])

        self.max_states = int(msg["max_states"])
        self.state = randint(0, self.max_states - 1)
        self.state_radiant_map: dict = {
            state: ((2 * pi * state) / self.max_states)
            for state in range(self.max_states)
        }
        # self.coupling_strength = float(msg["coupling_strength"])

        try:
            if msg["dynamic"] == "True":
                self.dynamic_cs = True
                self.gamma: int = int(msg["gamma"])
                self.avg_dist: int = int(msg["avg_dist"])
                self.dynamic_time: float = float(msg["dynamic_time"])
            else:
                self.dynamic_cs = False
        except KeyError:
            self.dynamic_cs = False

    def get_rad_from_state(self, state: int) -> float:
        return (2 * pi * state) / self.max_states

    def get_closest_state_from_rad(self, rad: float) -> int:
        state, _ = min(self.state_radiant_map.items(), key=lambda x: abs(rad - x[1]))

        return state

    async def calculate_step_distance(self, distance: int, gamma: float = 1):
        global start_time
        if time() - start_time < self.dynamic_time and (not self.dynamic_cs):
            return gamma
        else:
            max_dist: int = self.max_states // 2
            avg_dist = max_dist * 0.2

            return max(1, (self.gamma * (max_dist - distance) // (max_dist - avg_dist)))

    async def calculate_and_set_new_state(self, partner_state: int) -> None:
        global start_time

        partner_rad = self.get_rad_from_state(partner_state)

        average = (
            (2 * pi)
            + atan2(
                mean([sin(partner_rad), sin(self.get_rad_from_state(self.state))]),
                mean([cos(partner_rad), cos(self.get_rad_from_state(self.state))]),
            )
        ) % (2 * pi)

        avg_state = self.get_closest_state_from_rad(average)

        dist = abs(avg_state - self.state)
        if dist == 0:
            self.node.history["%.2f" % (time() - start_time)] = self.state
            return

        if self.dynamic_cs:
            step_distance = await self.calculate_step_distance(
                dist % (self.max_states // 2), gamma=self.gamma
            )
        else:
            step_distance = self.gamma

        if step_distance > dist:
            step_distance = dist

        if dist < self.max_states / 2:  # no wrap
            if self.state < avg_state:
                self.state = int((self.state + step_distance) % self.max_states)
            else:
                self.state = int((self.state - step_distance) % self.max_states)
        else:  # wrap
            if self.state < avg_state:
                self.state = int((self.state - step_distance) % self.max_states)
            else:
                self.state = int((self.state + step_distance) % self.max_states)

        self.node.history["%.2f" % (time() - start_time)] = self.state

    async def log_task(self):
        start = time()

        self.logging.set()
        while self.logging.is_set():
            self.node.history[
                "%.2f" % (time() - start)
            ] = (
                self.state
            )  # 2 digits after dot https://floating-point-gui.de/languages/python/
            await asyncio.sleep(0.05)

        await asyncio.sleep(10)
        await self.node.send_logs()

    async def start_synchronisation(self):
        global start_time
        print(f"start {self.run}")

        # task = asyncio.create_task(self.log_task())
        # self.background_tasks.add(task)
        # task.add_done_callback(self.background_tasks.discard)

        start_time = time()

        while time() - start_time < self.run_time:
            await asyncio.sleep(randint(10, 20) / 100)

            # send my state to random neighbor
            try:
                msg = json.dumps(
                    {
                        "type": "synchronization",
                        "operation": "synchro-request",
                        "state": self.state,
                    }
                )

                (
                    _,
                    writer,
                    reader,
                ) = await self.node.send_message_to_random_neighbor(msg)

                # wait for response and calculate new state
                res = await reader.read(2000)
                res = res.decode()

                await writer.drain()
                writer.close()

                res_dict = json.loads(res)

                await self.calculate_and_set_new_state(int(res_dict["state"]))
            except SendingMessageError:
                print("synchro failed")

        await asyncio.sleep(10)
        await self.node.send_logs()

        # self.logging.clear()

        # # flood end
        # msg: str = json.dumps({"type": "synchronization", "operation": "end"})
        # await self.node.send_message_to_all_neighbors(msg)
        # self.flooded_end = True

        return

    async def handle(self, msg: dict, writer: asyncio.StreamWriter):
        if msg["operation"] == "start":
            task = asyncio.create_task(self.start_synchronisation())
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)

            await writer.drain()
            writer.close()

        elif msg["operation"] == "synchro-request":
            _ = await self.handle_incoming_synchro(writer=writer, msg=msg)
        elif msg["operation"] == "end":

            _ = await self.handle_end_synchro(msg)
            await writer.drain()
            writer.close()

    async def handle_incoming_synchro(self, writer: asyncio.StreamWriter, msg: dict):
        # answer with my state
        response = json.dumps(
            {
                "type": "synchronization",
                "operation": "synchro-response",
                "state": self.state,
            }
        )

        writer.write(response.encode())
        await writer.drain()
        writer.close()

        # calculate and set new state
        await self.calculate_and_set_new_state(int(msg["state"]))

    async def handle_end_synchro(self, msg: dict) -> None:
        # END Logging by clearing event
        async with self.flooded_lck:
            self.logging.clear()
            if self.flooded_end == True:
                return None

            await self.node.send_message_to_all_neighbors(json.dumps(msg))
            self.flooded_end = True
            return None
