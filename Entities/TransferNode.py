from dataclasses import dataclass

@dataclass
class TransferNode:
    tx: str
    from_address: str
    to_address: str
    tokens: list[int]


