x = []
y = 0
while True:
    x.append(" " * 10_000_000)   # grows by ~10 MB each loop, forever
    y = y + 1
    print("ATTEMPT:", y)