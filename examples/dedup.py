"""Remove duplicates from a sorted linked list. Skipped nodes dim out
automatically — the compiler's reachability pass notices nothing points to
them and no variable holds them."""
import granim as ga


@ga.animate(debug=True, show=False)
def dedup(head):
    cur = head
    while cur is not None and cur.next is not None:
        if cur.next.value == cur.value:
            cur.next = cur.next.next   # unlink; orphan dims out
        else:
            cur = cur.next
    return head


if __name__ == "__main__":
    head = dedup(ga.linked_list([1, 1, 2, 3, 3, 3, 4]).head)
    out = []
    while head is not None:
        out.append(head.value)
        head = head.next
    print(out)
