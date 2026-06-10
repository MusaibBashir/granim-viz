"""Edit distance (Levenshtein) — the DP table fills cell by cell; reads pulse
the three cells each value depends on."""
import granim as ga

s, t = "kitten", "sit"
dp = ga.matrix([[0] * (len(t) + 1) for _ in range(len(s) + 1)])


@ga.animate(debug=True, show=False)
def edit_distance(s, t):
    for i in range(len(s) + 1):
        dp[i][0] = i
    for j in range(len(t) + 1):
        dp[0][j] = j
    for i in range(1, len(s) + 1):
        for j in range(1, len(t) + 1):
            if s[i - 1] == t[j - 1]:
                dp[i][j] = int(dp[i - 1][j - 1])
            else:
                dp[i][j] = 1 + min(int(dp[i - 1][j]), int(dp[i][j - 1]),
                                   int(dp[i - 1][j - 1]))
    dp[len(s)][len(t)].state = "done"
    return int(dp[len(s)][len(t)])


if __name__ == "__main__":
    print(edit_distance(s, t))
