import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List

class CLISystemAgent:
    """CLI System Controller for AI Godji.
    Allows Godji to execute shell commands, read, write, edit, and delete files.
    """

    @staticmethod
    def execute_command(command: str, cwd: str = None) -> Dict[str, Any]:
        """Execute a shell/PowerShell command on the local machine."""
        try:
            target_cwd = cwd if cwd and os.path.exists(cwd) else os.getcwd()
            # Use powershell on Windows, bash/sh on Unix
            shell_cmd = ["powershell", "-Command", command] if os.name == "nt" else command
            
            result = subprocess.run(
                shell_cmd if os.name == "nt" else command,
                shell=True if os.name != "nt" else False,
                capture_output=True,
                text=True,
                cwd=target_cwd,
                timeout=60
            )
            return {
                "status": "success" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "stdout": result.stdout[:4000],  # Truncate if too long
                "stderr": result.stderr[:4000]
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Command execution timed out (60s)."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def read_file(file_path: str, start_line: int = 1, line_count: int = 200) -> Dict[str, Any]:
        """Read text contents from a file."""
        try:
            path = Path(file_path).resolve()
            if not path.exists():
                return {"status": "error", "message": f"File '{file_path}' does not exist."}
            
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                
            total_lines = len(lines)
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, start_idx + line_count)
            snippet = "".join(lines[start_idx:end_idx])
            
            return {
                "status": "success",
                "file_path": str(path),
                "total_lines": total_lines,
                "start_line": start_idx + 1,
                "end_line": end_idx,
                "content": snippet
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def write_file(file_path: str, content: str, overwrite: bool = True) -> Dict[str, Any]:
        """Create or overwrite a file with specified content."""
        try:
            path = Path(file_path).resolve()
            if path.exists() and not overwrite:
                return {"status": "error", "message": f"File '{file_path}' already exists and overwrite is False."}
                
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
                
            return {"status": "success", "message": f"Successfully written to '{path}'", "file_path": str(path)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def edit_file(file_path: str, target_text: str, replacement_text: str) -> Dict[str, Any]:
        """Replace target text in an existing file."""
        try:
            path = Path(file_path).resolve()
            if not path.exists():
                return {"status": "error", "message": f"File '{file_path}' does not exist."}
                
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                
            if target_text not in content:
                return {"status": "error", "message": f"Target text not found in '{file_path}'."}
                
            new_content = content.replace(target_text, replacement_text, 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
                
            return {"status": "success", "message": f"Successfully updated '{path}'"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def delete_file(file_path: str) -> Dict[str, Any]:
        """Delete a file or directory on the machine."""
        try:
            path = Path(file_path).resolve()
            if not path.exists():
                return {"status": "error", "message": f"Path '{file_path}' does not exist."}
                
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
                
            return {"status": "success", "message": f"Successfully deleted '{path}'"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def list_directory(dir_path: str = ".") -> Dict[str, Any]:
        """List files and folders in a directory."""
        try:
            path = Path(dir_path).resolve()
            if not path.exists():
                return {"status": "error", "message": f"Directory '{dir_path}' does not exist."}
                
            items = []
            for entry in os.scandir(path):
                items.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": entry.stat().st_size if not entry.is_dir() else 0
                })
            return {"status": "success", "dir_path": str(path), "items": items}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Define tools schema for Gemini API Function Calling
CLI_TOOLS_DECLARATIONS = [
    {
        "name": "execute_command",
        "description": "Execute a terminal/PowerShell command on the system",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {"type": "STRING", "description": "The command string to execute"},
                "cwd": {"type": "STRING", "description": "Optional working directory path"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "read_file",
        "description": "Read text content from a file",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {"type": "STRING", "description": "Path to the file to read"}
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write or overwrite content to a file",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {"type": "STRING", "description": "Path of file to write"},
                "content": {"type": "STRING", "description": "Text content to write"}
            },
            "required": ["file_path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "Replace a block of text in an existing file",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {"type": "STRING", "description": "Path to file"},
                "target_text": {"type": "STRING", "description": "Exact text to find"},
                "replacement_text": {"type": "STRING", "description": "New text to insert"}
            },
            "required": ["file_path", "target_text", "replacement_text"]
        }
    },
    {
        "name": "delete_file",
        "description": "Delete a file or folder from the machine",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {"type": "STRING", "description": "Path to file or folder to delete"}
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "list_directory",
        "description": "List files and subdirectories inside a directory path",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "dir_path": {"type": "STRING", "description": "Directory path"}
            },
            "required": ["dir_path"]
        }
    }
]
