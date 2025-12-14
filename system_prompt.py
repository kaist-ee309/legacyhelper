"""System prompt for the AI agent."""

import platform

try:
    import distro
    DISTRO_AVAILABLE = True
except ImportError:
    DISTRO_AVAILABLE = False


def get_platform_info() -> str:
    """Get detailed platform information.

    Returns:
        Formatted string with OS, version, and architecture info.
    """
    system = platform.system()
    architecture = platform.machine()

    if system == "Linux" and DISTRO_AVAILABLE:
        distro_name = distro.name(pretty=True)
        distro_version = distro.version(pretty=True, best=True)
        distro_codename = distro.codename()
        kernel_version = platform.release()

        info_parts = [f"OS: {distro_name}"]
        if distro_version:
            info_parts.append(f"Version: {distro_version}")
        if distro_codename:
            info_parts.append(f"Codename: {distro_codename}")
        info_parts.append(f"Kernel: {kernel_version}")
        info_parts.append(f"Architecture: {architecture}")

        return "\n".join(info_parts)

    elif system == "Darwin":
        mac_version = platform.mac_ver()[0]
        return f"OS: macOS {mac_version}\nArchitecture: {architecture}"

    elif system == "Windows":
        win_version = platform.version()
        win_release = platform.release()
        return f"OS: Windows {win_release}\nVersion: {win_version}\nArchitecture: {architecture}"

    else:
        return f"OS: {system}\nArchitecture: {architecture}"


PLATFORM_INFO = get_platform_info()

SYSTEM = f"""
You are a helpful assistant that helps trouble shooting legacy linux/unix systems.
User doesn't know much about linux/unix systems, you should always explain the problem in a way that is easy to understand.
You should always give the user the best possible solution to the problem.
You should run appropriate commands to troubleshoot the problem.
You don't have to ask user for confirmation before using tools.
Always place the solution at last and explicitly define variables like path, file, etc.
Check the system error log when lack of context from all other tools.
Clearly define the order of commands to be executed for troubleshooting.
Always think two steps ahead and give the user the best possible solution.
When output contains code, always include the language tag in the code block.
For example, if the code is for bash, use ```bash``` to wrap the code.
If the code is for python, use ```python``` to wrap the code.
If the code is for javascript, use ```javascript``` to wrap the code.
If the code is for html, use ```html``` to wrap the code.
If the code is for css, use ```css``` to wrap the code.
If the code is for json, use ```json``` to wrap the code.
If the code is for xml, use ```xml``` to wrap the code.
If the code is for yaml, use ```yaml``` to wrap the code.

---
User's System Information:
{PLATFORM_INFO}
---
"""