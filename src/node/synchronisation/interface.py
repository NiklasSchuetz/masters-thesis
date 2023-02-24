from dataclasses import dataclass


class Synchronisation_Interface:
    def handle_message(self, msg: str):
        """handle incoming message json string: type == synchronisation"""
        pass


class SendingMessageError(Exception):
    pass


@dataclass
class Logentry:
    run_id: int
    node_id: int
    partner_id: int
    new_value: float
    synchro_done: int
