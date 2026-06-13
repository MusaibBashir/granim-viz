"""Preorder traversal with built-in tree nodes.

This example uses ga.TreeNode instead of a custom LeetCode-style node so the
tree gets Granim's tidy tree layout. A separate output array fills in the exact
order visited: node, left subtree, right subtree.
"""
import granim as ga


@ga.animate(debug=True, show=False, title="Preorder traversal")
def preorder(root, out, write=0):
    if root is None:
        return write

    root.state = "active"
    out[write] = root.value
    out[write].state = "done"
    write += 1

    root.state = "visited"
    write = preorder(root.left, out, write)
    write = preorder(root.right, out, write)

    root.state = "done"
    return write


def sample_tree():
    #          8
    #       /     \
    #      3       10
    #     / \        \
    #    1   6        14
    #       / \      /
    #      4   7    13
    t = ga.tree()
    n8 = ga.TreeNode(8)
    n3 = ga.TreeNode(3)
    n10 = ga.TreeNode(10)
    n1 = ga.TreeNode(1)
    n6 = ga.TreeNode(6)
    n14 = ga.TreeNode(14)
    n4 = ga.TreeNode(4)
    n7 = ga.TreeNode(7)
    n13 = ga.TreeNode(13)

    t.root = n8
    n8.left, n8.right = n3, n10
    n3.left, n3.right = n1, n6
    n10.right = n14
    n6.left, n6.right = n4, n7
    n14.left = n13
    return t


if __name__ == "__main__":
    tree = sample_tree()
    output = ga.array([""] * 9)
    preorder(tree.root, output)
    print(output.to_list())
