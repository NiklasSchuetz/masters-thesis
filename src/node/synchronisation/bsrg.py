from random import randint
from statistics import mean, StatisticsError

from .interface import Synchronisation_Interface, SendingMessageError
import asyncio
from math import atan2, pi, cos, sin
import json
from time import time


start_time: float = 0


class BSRG(Synchronisation_Interface):
    def __init__(self, node) -> None:
        super().__init__()
        self.node = node

        self.run: str = None
        self.run_time: float = None

        self.max_states: int
        self.state: int

        self.neighborstates: dict = {}  # id: state
        self.state_radiant_map: dict = {}

        self.dynamic_cs: bool = False
        self.gamma: int = 1
        self.avg_dist: int = None
        self.dynamic_time: float = None

        # self.coupling_strength: int = None

        self.logging = asyncio.Event()

        self.flooded_end = False
        self.flooded_lck = asyncio.Lock()
        self.background_tasks = set()  # needed cause asyncio is :(

    def register_new_config(self, msg: dict) -> None:
        self.run = msg["run"]
        self.run_time = float(msg["time"])

        self.max_states = int(msg["max_states"])
        self.state = randint(0, self.max_states - 1)
        self.state_radiant_map: dict = {
            state: ((2 * pi * state) / self.max_states)
            for state in range(self.max_states)
        }
        self.coupling_strength = float(msg["coupling_strength"])

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

    def get_radiant_from_state(self, state: int) -> float:
        return (2 * pi * state) / self.max_states

    async def calculate_hamiltonian(self, neighborstates: dict = None) -> float:
        if neighborstates == None:
            neighborstates = self.neighborstates

        hamiltonian: float = 0
        for _, neighbor_state in self.neighborstates.items():
            hamiltonian += cos(
                self.get_radiant_from_state(self.state)
                - self.get_radiant_from_state(neighbor_state)
            )

        return hamiltonian

    def get_closest_state_from_rad(self, rad: float) -> int:
        state, _ = min(self.state_radiant_map.items(), key=lambda x: abs(rad - x[1]))

        return state

    async def calculate_step_distance(self, distance: int, gamma: float = None):
        global start_time
        if time() - start_time < self.dynamic_time:
            return gamma
        else:
            max_dist: int = self.max_states // 2
            avg_dist = max_dist // 2

            return max(1, (gamma * (max_dist - distance) // (max_dist - avg_dist)))

    async def notify_neighbors_of_new_state(self, is_initial_state: bool = False):
        msg = json.dumps(
            {
                "type": "synchronization",
                "operation": "new_neighbor-state",
                "id": f"{self.node.id}",
                "state": f"{int(self.state)}",
            }
        )

        while True:
            try:
                await self.node.send_message_to_all_neighbors(msg)
                return
            except SendingMessageError:
                # if is_initial_state:
                await asyncio.sleep(0.1)
                continue

    def update_neighbor_state(self, neighbor_id: str, neighbor_state: int):
        self.neighborstates[neighbor_id] = neighbor_state

    async def log_task(self):
        start = time()

        self.logging.set()
        while self.logging.is_set():
            self.node.history[
                "%.2f" % (time() - start)
            ] = (
                self.state
            )  # 2 digits after dot https://floating-point-gui.de/languages/python/
            await asyncio.sleep(0.1)

        await asyncio.sleep(3)
        await self.node.send_logs()

    def log_state(self):
        global start_time
        self.node.history["%.2f" % (time() - start_time)] = self.state

    async def start_synchronisation(self):
        global start_time

        print(f"start synchro: {self.run}")
        start_time = time()

        # task = asyncio.create_task(self.log_task())
        # self.background_tasks.add(task)
        # task.add_done_callback(self.background_tasks.discard)

        start_time = time()
        while time() - start_time < self.run_time:
            await asyncio.sleep(randint(2, 7) / 10)
            await self.synchronization_step()
            self.log_state()

        # self.logging.clear()

        await self.node.send_logs()

    async def synchronization_step_brute_force_hamiltonian(self):
        calc_hamiltonians = []
        for s in range(self.max_states):
            hamiltonian = 0
            for _, neighbor_state in self.neighborstates.items():
                hamiltonian += cos(
                    self.get_radiant_from_state(s)
                    - self.get_radiant_from_state(neighbor_state)
                )

            calc_hamiltonians.append(hamiltonian)

        state_with_lowest_hamiltonian = calc_hamiltonians.index(max(calc_hamiltonians))

        self.state = state_with_lowest_hamiltonian

    async def synchronization_step(self):
        """Look at neighbor states and find the state which minimalizes the hamiltonian"""

        radians_neighbors = [
            self.get_radiant_from_state(s) for s in self.neighborstates.values()
        ]

        x_list = []
        y_list = []
        for rad in radians_neighbors:
            x_list.append(cos(rad))
            y_list.append(sin(rad))

        try:
            average = ((2 * pi) + atan2(mean(y_list), mean(x_list))) % (2 * pi)
        # average as a positive radian in range [0,2pi)
        except StatisticsError as e:
            # mean requires at least one data point
            print(e)
            await asyncio.sleep(1)
            return

        if False:
            # my_rad = self.get_radiant_from_state(self.state)
            # rad annäherung
            # dist = average - my_rad

            # if abs(dist) < pi:
            #     new_rad = my_rad + self.coupling_strength * (dist)
            # elif abs(dist) > pi:  # wrap around
            #     new_rad = (
            #         ((my_rad + 2 * pi) - self.coupling_strength * ((2 * pi) - dist))
            #         % 2
            #         * pi
            #     )
            # new_state = self.get_closest_state_from_rad(new_rad)
            pass

        avg_state = self.get_closest_state_from_rad(average)

        before = self.state

        dist = abs(avg_state - self.state)
        if dist == 0:
            self.log_state()
            return

        if self.dynamic_cs:
            step_distance = await self.calculate_step_distance(
                dist % (self.max_states // 2), gamma=self.gamma
            )
        else:
            step_distance = 1

        if step_distance > dist:
            step_distance = dist

        if dist < self.max_states / 2:  # no wrap
            if self.state < avg_state:
                self.state = (self.state + step_distance) % self.max_states
            else:
                self.state = (self.state - step_distance) % self.max_states
        else:  # wrap
            if self.state < avg_state:
                self.state = (self.state - step_distance) % self.max_states
            else:
                self.state = (self.state + step_distance) % self.max_states

        self.log_state()
        print(f"from: {before} to: {self.state} avg: {avg_state}")

        await self.notify_neighbors_of_new_state()

    async def handle(self, msg: dict, writer: asyncio.StreamWriter):
        writer.close()
        if msg["operation"] == "new_neighbor-state":
            self.update_neighbor_state(
                neighbor_id=msg["id"], neighbor_state=int(msg["state"])
            )
        if msg["operation"] == "share_state":
            await self.notify_neighbors_of_new_state()
            print("neighbors notified of initial state")
        elif msg["operation"] == "start":
            task = asyncio.create_task(self.start_synchronisation())
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)

        elif msg["operation"] == "end":
            _ = await self.handle_end_synchro(writer, msg)

    async def handle_end_synchro(self, writer: asyncio.StreamWriter, msg: dict) -> None:
        # closing writer
        await writer.drain()
        writer.close()
        await writer.wait_closed()

        # END Logging by clearing event
        async with self.flooded_lck:
            self.logging.clear()
            if self.flooded_end == True:  # return early if already set
                return None

            await self.node.send_message_to_all_neighbors(json.dumps(msg))
            self.flooded_end = True
            return None
