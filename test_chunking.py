import math
container_ids = list(range(100))
chunk_size = 30
for i in range(0, len(container_ids), chunk_size):
    chunk = container_ids[i:i + chunk_size]
    print(chunk)
