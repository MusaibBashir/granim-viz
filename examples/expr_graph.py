"""A micrograd-style scalar expression as a real computation graph.

Each Value is a custom node; its `children` field holds the operands it was
built from. @ga.node(graph=True) turns that web into one laid-out graph -- the
same renderer ga.graph uses -- instead of a floating chain of labelled edges.
ga.note() narrates each step on the canvas.
"""
import granim as ga


@ga.node(value="label", shape="circle", graph=True)
class Value:
    def __init__(self, data, label="", children=()):
        self.data = data
        self.label = f"{label} {data:+.2f}".strip()
        self.children = list(children)   # public node field -> graph edges

    def __add__(self, other):
        return Value(self.data + other.data, "+", (self, other))

    def __mul__(self, other):
        return Value(self.data * other.data, "×", (self, other))


@ga.animate(debug=True, show=False, title="expression graph")
def forward():
    a, b, c = Value(2.0, "a"), Value(-3.0, "b"), Value(10.0, "c")
    ga.note("Inputs a, b, c — leaves of the graph.")
    e = a * b
    ga.note("e = a × b links back to both operands.")
    L = e + c
    ga.note("L = e + c. One DAG, laid out like a built-in graph.")
    return L


if __name__ == "__main__":
    forward()
