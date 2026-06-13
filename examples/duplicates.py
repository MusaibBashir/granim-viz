from typing import Optional
import granim as ga


@ga.node(value="val", shape="pill")
class ListNode:
    def __init__(self, x):
        self.val = x
        self.next = None

class Solution:
    @ga.animate(debug=True, show=True, title="Delete Duplicates from Sorted List", theme="dark")
    def deleteDuplicates(self, head: Optional[ListNode]) -> Optional[ListNode]:
        if not head:
            return head
        
        curr = head
        while curr and curr.next:
            if curr.val == curr.next.val:
                curr.next = curr.next.next
            else:
                curr = curr.next
                
        return head

a = ListNode(1)
b = ListNode(2)
c = ListNode(2)
d = ListNode(3) 
e = ListNode(3)
f = ListNode(4)

a.next = b
b.next = c
c.next = d
d.next = e
e.next = f

print(Solution().deleteDuplicates(a))