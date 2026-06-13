import granim as ga
from typing import List, Optional

@ga.node(value="val", shape="pill")
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

class Solution:
    @ga.animate(debug=True, show=True, title="Preorder Traversal", theme="dark")
    def preorderTraversal(self, root: Optional[TreeNode]) -> List[int]:
        stack = []
        ans = []
        curr = root

        while curr or stack:
            while curr:
                ans.append(curr.val)  
                stack.append(curr)
                curr = curr.left     
            node = stack.pop()
            curr = node.right         
        return ans
a = TreeNode(3)
b = TreeNode(2)
c = TreeNode(0)
d = TreeNode(-4)
e = TreeNode(1)
f = TreeNode(4)
g= TreeNode(5)
h= TreeNode(6)

a.left = b
b.left = c
c.left = d
a.right = e
b.right = f
e.right = g
e.left = h


print(Solution().preorderTraversal(a))