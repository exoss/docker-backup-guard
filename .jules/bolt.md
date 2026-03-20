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
