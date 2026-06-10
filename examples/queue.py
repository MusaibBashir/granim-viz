"""A user-owned queue: @ga.node nodes + @ga.container for the wrapper.
head/tail render as floating badges that follow their nodes, and dequeued
nodes dim out once nothing holds them."""
import granim as ga


@ga.node(value="val", shape="pill")
class QNode:
    def __init__(self, val):
        self.val = val
        self.next = None


@ga.container
class Queue:
    def __init__(self):
        self.head = None
        self.tail = None

    def enqueue(self, v):
        n = QNode(v)
        if self.tail is not None:
            self.tail.next = n
        else:
            self.head = n
        self.tail = n

    def dequeue(self):
        n = self.head
        self.head = n.next
        n.next = None
        return n.val


@ga.animate(debug=True, show=False)
def queue_demo():
    q = Queue()
    for v in (1, 2, 3, 4, 5):
        q.enqueue(v)
    out = [q.dequeue(), q.dequeue()]
    q.enqueue(6)
    return out


if __name__ == "__main__":
    print(queue_demo())
