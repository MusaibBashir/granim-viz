"""Recursive linked-list reversal — the headline demo. Watch the call stack
descend to null, then the arrows flip one by one as it unwinds."""
import granim as ga


@ga.animate(debug=True, show=False)
def reverse_recursive(node):
    if node is None or node.next is None:
        return node
    new_head = reverse_recursive(node.next)
    node.next.next = node     # flip: classified edge_flip (reverse edge alive)
    node.next = None
    return new_head


if __name__ == "__main__":
    head = reverse_recursive(ga.linked_list([1, 2, 3, 4, 5]).head)
    print("new head:", head)
