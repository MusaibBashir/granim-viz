"""Floyd's tortoise-and-hare cycle detection. The slow/fast badges chase each
other around the cycle and stack on the meeting node. The cycle edge renders
as a backward arc automatically."""
import granim as ga

ll = ga.linked_list([1, 2, 3, 4, 5, 6])
nodes = list(ll)          # plain iteration; no recorder active, no events
nodes[-1].next = nodes[2]  # 6 -> 3: make it cyclic


@ga.animate(debug=True, show=False)
def has_cycle(head):
    slow = fast = head
    while fast is not None and fast.next is not None:
        slow = slow.next
        fast = fast.next.next
        if slow is fast:
            return True
    return False


if __name__ == "__main__":
    print("cycle:", has_cycle(ll.head))
