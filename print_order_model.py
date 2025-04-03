
from datetime import datetime
from collections import deque

class PrintOrder:
    def __init__(self, order_id, copies, layout, print_type, print_sides, expected_datetime):
        self.order_id = order_id
        self.copies = copies
        self.layout = layout
        self.print_type = print_type
        self.print_sides = print_sides
        self.expected_datetime = expected_datetime
        self.arrival_time = datetime.now()

    def __lt__(self, other):
        if self.arrival_time == other.arrival_time:
            return self.copies < other.copies
        return self.arrival_time < other.arrival_time

order_queue = deque()

def add_order(order):
    order_queue.append(order)
    order_queue = deque(sorted(order_queue))
