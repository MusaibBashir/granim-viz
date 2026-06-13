from typing import Optional
import granim as ga


class Solution:
    @ga.animate(debug=True, show=True, title="Detect Cycle in Linked List")
    def hasCycle(self, head: Optional[ga.ListNode]) -> bool:
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


ll = ga.linked_list([3, 2, 0, -4,5,6,8])
nodes = list(ll)
nodes[-1].next = nodes[1]   # create cycle: -4 -> 2

print(Solution().hasCycle(ll.head))