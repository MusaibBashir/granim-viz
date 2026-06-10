"""BST insertion — tidy tree layout re-flows as nodes attach."""
import granim as ga


@ga.animate(debug=True, show=False)
def build_bst(t, values):
    for v in values:
        node = ga.TreeNode(v)
        if t.root is None:
            t.root = node
            continue
        cur = t.root
        while True:
            if v < cur.value:
                if cur.left is None:
                    cur.left = node
                    break
                cur = cur.left
            else:
                if cur.right is None:
                    cur.right = node
                    break
                cur = cur.right
    return t


if __name__ == "__main__":
    build_bst(ga.tree(), [50, 30, 70, 20, 40, 60, 80, 35, 65])
