from random import randint, uniform
from statistics import StatisticsError, mean
from .interface import Synchronisation_Interface, SendingMessageError
import asyncio
from math import atan2, pi, cos, exp, sin
import json
from time import time

k: float = 1.380649e-23
start_time = None  # used to store the time at the start of the synchronization


class MetroHasting(Synchronisation_Interface):
    def __init__(self, node) -> None:
        super().__init__()
        self.node = node

        self.max_states: int
        self.state: int
        self.neighborstates: dict = {}  # id: state

        self.temperature: float = None
        self.background_tasks = set()  # needed cause asyncio is :(
        self.current_run = None
        self.logging = asyncio.Event()
        self.use_random_neighbor_state: bool = False

    def register_new_config(self, msg: dict) -> None:
        self.max_states = int(msg["max_states"])
        self.state = randint(0, self.max_states - 1)
        self.state_radiant_map: dict = {
            state: ((2 * pi * state) / self.max_states)
            for state in range(self.max_states)
        }
        self.temperature = float(msg["temperature"])
        self.run = msg["run"]
        self.run_time = float(msg["time"])
        try:
            if msg["random_neighbor"] == "True":
                self.use_random_neighbor_state = True
            else:
                self.use_random_neighbor_state = False
        except KeyError:
            self.use_random_neighbor_state = False

    def get_radiant_from_state(self, state: int) -> float:
        return (2 * pi * state) / self.max_states

    def get_closest_state_from_rad(self, rad: float) -> int:
        state, _ = min(self.state_radiant_map.items(), key=lambda x: abs(rad - x[1]))

        return state

    async def calculate_hamiltonian(
        self, neighborstates: dict = None, my_state: int = -1
    ) -> float:

        if neighborstates == None:
            neighborstates = self.neighborstates
        if my_state == -1:
            my_state = self.state

        hamiltonian: float = 0
        for _, neighbor_state in self.neighborstates.items():
            hamiltonian += cos(
                self.get_radiant_from_state(my_state)
                - self.get_radiant_from_state(neighbor_state)
            )

        hamiltonian *= -1

        return hamiltonian

    async def notify_neighbors_of_new_state(self):

        msg = json.dumps(
            {
                "type": "synchronization",
                "operation": "new_neighbor-state",
                "id": f"{self.node.id}",
                "state": f"{self.state}",
            }
        )

        while True:
            try:
                await self.node.send_message_to_all_neighbors(msg)
                return
            except SendingMessageError:
                # if is_initial_state:
                await asyncio.sleep(0.2)
                continue

    def update_neighbor_state(self, neighbor_id: int, neighbor_state: int):
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
            await asyncio.sleep(0.05)

        await asyncio.sleep(3)
        await self.node.send_logs()

    def log_state(self):
        global start_time
        self.node.history["%.2f" % (time() - start_time)] = self.state

    async def start_synchronisation(self):
        global start_time

        await self.notify_neighbors_of_new_state()

        print(f"start synchro: {self.run}")

        # task = asyncio.create_task(self.log_task())
        # self.background_tasks.add(task)
        # task.add_done_callback(self.background_tasks.discard)
        start_time = time()
        while time() - start_time < self.run_time:
            await asyncio.sleep(randint(2, 7) / 10)
            await self.synchronisation_step()

        await self.node.send_logs()

    async def synchronisation_step(self):
        """m algo: random state: accept if new hamiltonian is lower"""
        global k

        cur_hamiltonian: float = await self.calculate_hamiltonian()

        # Brute Force Hamiltonians

        # if self.use_random_neighbor_state:
        #     neighbor_id: int = self.node.get_random_neighbor()
        #     neighbor_state: int = self.neighborstates[neighbor_id]

        #     if neighbor_state == self.state:
        #         return

        #     new_state: int = neighbor_state
        #     new_hamiltonian: float = await self.calculate_hamiltonian(
        #         my_state=new_state
        #     )
        # else:  # choose random state
        #     new_state: int = randint(0, self.max_states - 1)

        #     new_hamiltonian: float = await self.calculate_hamiltonian(
        #         my_state=new_state
        #     )

        # Efficient method for vector Potts model
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

        avg_state = self.get_closest_state_from_rad(average)

        new_hamiltonian: float = await self.calculate_hamiltonian(my_state=avg_state)

        delta_h: float = new_hamiltonian - cur_hamiltonian

        if delta_h <= 0:
            self.state = avg_state
            await self.notify_neighbors_of_new_state()
        else:
            try:
                exp_term = exp(-(delta_h / (k * self.temperature)))
            except ZeroDivisionError:
                exp_term = 0

            chance = uniform(0.0, 1)
            if chance < min(1, exp_term):
                print(
                    f"accept bigger {self.state} -> {avg_state} : {'%.2f' % chance} < {exp_term} | delta {delta_h} {k*self.temperature}"
                )
                self.state = avg_state
                await self.notify_neighbors_of_new_state()

        self.log_state()

    async def handle(self, msg: dict, writer: asyncio.StreamWriter):
        writer.close()

        if msg["operation"] == "new_neighbor-state":
            self.update_neighbor_state(
                neighbor_id=int(msg["id"]), neighbor_state=int(msg["state"])
            )
        if msg["operation"] == "start":
            task = asyncio.create_task(self.start_synchronisation())
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)
