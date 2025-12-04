from pydantic import BaseModel
from pydantic_ai import RunContext, Tool, Agent
from pydantic_ai import FunctionToolset
import subprocess

class BashResult(BaseModel):
    stdout: str
    stderr: str
    returncode: int

class Exec_Deps(BaseModel):
    workdir: str

def bash_tool(command: str) -> BashResult:
    """
    Run a bash command on the local machine.

    Parameters
    ----------
    command:
        The shell command to execute (read-only commands only).
    """
    # simple safety guard example (extend this a lot in real code!)
    forbidden = ["rm -rf", "shutdown", "reboot", ":(){:|:&};:"]
    if any(f in command for f in forbidden):
        return BashResult(
            stdout="",
            stderr="Blocked dangerous command",
            returncode=1,
        )
    
    print (f"[TOOL CALL]: command={command}")
    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = proc.communicate()
    return BashResult(stdout=out, stderr=err, returncode=proc.returncode)

system_log_toolset = FunctionToolset(tools = [])

@system_log_toolset.tool
def get_current_system_log() -> str:
    """
    Get the system log for the current boot.
    """
    return subprocess.run(["journalctl", "-p", "3", "-xb", "--no-pager"], capture_output=True, text=True).stdout

@system_log_toolset.tool
def get_previous_system_log() -> str:
    """
    Get the system log for the previous boot.
    """
    return subprocess.run(["journalctl", "-p", "3", "-xb", "-1", "--no-pager"], capture_output=True, text=True).stdout


SYSTEM_LOG_TOOLSET = system_log_toolset

bash_tool = Tool(
    bash_tool,
    name="bash",
    description="Run safe bash commands in the configured working directory.",
    takes_ctx=False,
)