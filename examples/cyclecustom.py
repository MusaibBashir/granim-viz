from typing import Optional
import granim as ga


@ga.node(value="val", shape="pill")
class ListNode:
    def __init__(self, x):
        self.val = x
        self.next = None

class Solution:
    @ga.animate(debug=True, show=True, title="Detect Cycle in Linked List", theme="light")
    def hasCycle(self, head: Optional[ListNode]) -> bool:
        if not head or not head.next:
            return False

        slow = head
        fast = head

        while fast and fast.next:
            slow = slow.next
            fast = fast.next.next

            if slow == fast:
                return True

        return False

a = ListNode(3)
b = ListNode(2)
c = ListNode(0)
d = ListNode(-4)

a.next = b
b.next = c
c.next = d
d.next = b   # cycle

print(Solution().hasCycle(a))