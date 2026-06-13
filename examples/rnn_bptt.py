"""Karpathy's min-char-rnn, unrolled and animated (hidden_size=1, vocab "ab",
so every tensor is a real scalar and the math is exact, not mocked).

Two separate, titled graphs make the two passes legible on their own:

  Forward   — x_t feeds h_t via Wxh, h_{t-1} feeds h_t via Whh (the recurrence),
              h_t feeds the output via Why. Node labels are real activations.
  Backward  — a *second* graph built during BPTT: dy_t feeds dh_t via Why, and
              dh_{t+1} feeds dh_t via Whh — that edge is dhnext hopping one step
              back in time. Watch the gradients accumulate in the panel.
"""
import math

import granim as ga

VOCAB = "ab"
SEQ = [0, 1, 1, 0]      # "abba"
TARGETS = [1, 1, 0, 0]  # next char at each step: "bbaa"

fwd = ga.graph(directed=True, title="Forward  ·  activations")
bwd = ga.graph(directed=True, title="Backward  ·  gradients (BPTT)")
onehot = ga.matrix([[0] * len(SEQ) for _ in VOCAB])  # vocab x time


@ga.animate(debug=True, show=False, title="RNN forward + BPTT")
def rnn_bptt(inputs, targets):
    Wxh = [0.9, -0.6]      # 1x2: input -> hidden, one column per char
    Whh = 0.7              # 1x1: hidden -> hidden (the recurrence)
    Why = [1.3, -1.3]      # 2x1: hidden -> output logits
    bh, by0, by1 = 0.1, 0.0, 0.0

    h = 0.0
    hn = [fwd.add_node("h-1=0.00")]
    hn[0].state = "visited"
    xn, yn, hs, ps = [], [], [0.0], []
    loss = 0.0

    # forward pass
    ga.note("Forward: the activation graph grows one timestep at a time.")
    for t in range(len(inputs)):
        c = inputs[t]
        onehot[c][t] = 1                 # one-hot encode input character
        onehot[c][t].state = "visited"
        xn.append(fwd.add_node(f"x{t}='{VOCAB[c]}'"))
        xn[t].state = "visited"
        h = math.tanh(Wxh[c] + Whh * h + bh)   # hidden state update
        hs.append(h)
        hn.append(fwd.add_node(f"h{t}={h:+.2f}"))
        fwd.add_edge(xn[t], hn[t + 1], weight="Wxh")
        fwd.add_edge(hn[t], hn[t + 1], weight="Whh")
        hn[t + 1].state = "visited"
        y0, y1 = Why[0] * h + by0, Why[1] * h + by1   # output logits
        e0, e1 = math.exp(y0), math.exp(y1)
        p = (e0 / (e0 + e1), e1 / (e0 + e1))          # softmax probabilities
        ps.append(p)
        yn.append(fwd.add_node(f"p('{VOCAB[targets[t]]}')={p[targets[t]]:.2f}"))
        fwd.add_edge(hn[t + 1], yn[t], weight="Why")
        loss += -math.log(p[targets[t]])              # cross-entropy loss

    # backward pass (BPTT) -- a separate graph, walked in reverse time
    ga.note("Backward: a second graph; the Whh edge is dhnext hopping to t-1.")
    dWxh0, dWxh1, dWhh, dWhy0, dWhy1 = 0.0, 0.0, 0.0, 0.0, 0.0
    dhnext = 0.0
    dh_prev = None                       # dh node from the later timestep (t+1)
    for t in reversed(range(len(inputs))):
        dy0, dy1 = ps[t][0], ps[t][1]
        if targets[t] == 0:
            dy0 -= 1                     # softmax + cross-entropy gradient
        else:
            dy1 -= 1
        dy = dy0 if targets[t] == 0 else dy1
        yn[t].state = "active"           # spotlight the forward output we hit
        dyn = bwd.add_node(f"dy{t}={dy:+.2f}")
        dyn.state = "active"
        dWhy0 += dy0 * hs[t + 1]
        dWhy1 += dy1 * hs[t + 1]
        dh = Why[0] * dy0 + Why[1] * dy1 + dhnext  # gradient flows through h
        dhraw = (1 - hs[t + 1] * hs[t + 1]) * dh   # tanh backward: (1-tanh^2)
        dhn = bwd.add_node(f"dh{t}={dh:+.2f}")
        dhn.state = "done"
        bwd.add_edge(dyn, dhn, weight="Why")
        if dh_prev is not None:                     # dhnext: t+1 -> t through Whh
            bwd.add_edge(dh_prev, dhn, weight="Whh")
        dh_prev = dhn
        hn[t + 1].value = f"dh={dh:+.2f}"
        hn[t + 1].state = "done"
        if inputs[t] == 0:
            dWxh0 += dhraw
        else:
            dWxh1 += dhraw
        dWhh += dhraw * hs[t]
        dhnext = Whh * dhraw             # gradient for previous hidden state
        hn[t].state = "frontier"         # dhnext has arrived at h_{t-1}
    return loss, dWhh, dWxh0, dWhy0


if __name__ == "__main__":
    loss, dWhh, dWxh0, dWhy0 = rnn_bptt(SEQ, TARGETS)
    print(f"loss={loss:.4f}  dWhh={dWhh:+.4f}  dWxh[a]={dWxh0:+.4f}  dWhy[0]={dWhy0:+.4f}")
