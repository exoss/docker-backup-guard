import re

with open('app/engine.py', 'r') as f:
    content = f.read()

# Add class constants just once
if "CRITICAL_SUB_PATHS" not in content:
    constants = """
    # Define excluded system paths that should NEVER be backed up
    # Using frozenset for O(1) lookup
    EXCLUDED_PATHS = frozenset([
        "/", "/proc", "/sys", "/dev", "/run", "/tmp",
        "/var/run", "/var/lib/docker", "/etc/localtime", "/etc/timezone",
        "/var/run/docker.sock"
    ])

    # Critical sub-paths as a constant tuple for optimized .startswith() checks
    CRITICAL_SUB_PATHS = ("/proc/", "/sys/", "/dev/", "/run/")
"""
    content = content.replace("class BackupEngine:", "class BackupEngine:" + constants, 1)

# Remove local EXCLUDED_PATHS
pattern = r"[ ]+# Define excluded system paths that should NEVER be backed up\n[ ]+EXCLUDED_PATHS = \[\n[ ]+\"/\", \"/proc\", \"/sys\", \"/dev\", \"/run\", \"/tmp\", \n[ ]+\"/var/run\", \"/var/lib/docker\", \"/etc/localtime\", \"/etc/timezone\",\n[ ]+\"/var/run/docker.sock\"\n[ ]+\]\n[ ]+"
content = re.sub(pattern, "", content)

# Update usage
content = content.replace("if source in EXCLUDED_PATHS:", "if source in self.EXCLUDED_PATHS:")
content = content.replace('if source.startswith(("/proc/", "/sys/", "/dev/", "/run/")):', 'if source.startswith(self.CRITICAL_SUB_PATHS):')

with open('app/engine.py', 'w') as f:
    f.write(content)
