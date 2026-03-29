## 2024-03-16 - Avoid N+1 API Calls with docker-py Container Objects
**Learning:** In the `docker` python library, accessing the `container.image` property on a `Container` object retrieved via `client.containers.list()` triggers a lazy-loading API call to fetch the image details. When iterating over many containers, this causes a severe N+1 API call performance bottleneck.
**Action:** Always access pre-loaded image attributes directly via the container's attributes dictionary (e.g., `container.attrs.get('Config', {}).get('Image')` or `container.attrs.get('Image')`) instead of the lazy `container.image` property to avoid extra API requests.

## 2024-05-24 - Optimize directory iteration with `os.scandir` over `os.listdir`
**Learning:** Using `os.listdir` returns just a list of names, requiring subsequent `os.path.isfile`, `os.path.getmtime`, or `os.path.getsize` calls for each entry. These extra `stat()` system calls can cause noticeable performance overhead, especially in directories with many files like a backup storage path.
**Action:** Always use `os.scandir()` instead of `os.listdir()` when iterating directories and checking file properties, as `os.scandir()` caches the `DirEntry` metadata (like file type and attributes), heavily reducing the number of `stat()` system calls.

## 2024-11-06 - Avoid reading entire log files into memory
**Learning:** In Python, reading the last N lines of a file using `f.readlines()[-N:]` reads the entire file content into memory. This causes massive memory overhead and CPU usage spikes when the log file (e.g., `logs/app.log`) grows over time because log rotation is not configured.
**Action:** Use `collections.deque(f, maxlen=N)` to iterate over the file efficiently, which limits the memory usage to O(1) proportional to N, rather than O(M) proportional to the file size M.


## 2025-02-28 - Use @st.cache_resource for Streamlit complex object caching
**Learning:** Streamlit's `@st.cache_data` uses `pickle` to serialize and deserialize the returned objects on every read. When caching complex class instances with network clients (like Docker `Container` objects), this causes massive CPU/memory overhead and potential detached-client bugs upon unpickling.
**Action:** Always use `@st.cache_resource` instead of `@st.cache_data` when caching un-serializable or complex objects like network clients, database connections, or Docker objects. It stores the direct memory reference without pickling overhead, significantly improving application responsiveness.

## 2025-03-05 - Use server-side filtering in Docker Python client
**Learning:** Calling `self.client.containers.list()` fetches the metadata and creates `Container` objects for ALL containers running on the Docker host, which causes massive overhead if you only need a subset based on a specific label. Filtering client-side is an anti-pattern.
**Action:** Always use the Docker API's built-in server-side filtering (e.g., `self.client.containers.list(filters={"label": "backup.enable=true"})`) to reduce network payload size, memory usage, and object instantiation time significantly.
## 2024-05-24 - Bulk List Docker Containers
**Learning:** `docker.client.containers.list` defaults to only returning running containers unless `all=True` is provided, which can mask bugs when optimizing bulk loads where non-running containers (e.g. paused, restarting, exited) must be captured.
**Action:** Always include `all=True` when bulk loading states of a diverse group of containers from the Docker SDK, unless we strictly filter for running containers.
## 2025-03-05 - Parallelize I/O Bound Docker Operations
**Learning:** Docker container `stop` and `start` operations are I/O bound and can take significant time (up to 10 seconds for graceful stops). Running these sequentially in a loop for a large stack creates a massive performance bottleneck during backup processes.
**Action:** Use `concurrent.futures.ThreadPoolExecutor` to parallelize container state changes (like stop/start). Always ensure `max_workers` is bounded (e.g., `min(len(items), 10)`), check for empty lists before initializing the executor, and use `list(executor.map(...))` to preserve order and capture exceptions safely.
