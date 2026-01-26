"""Editor integration utilities for QuantCoder CLI."""

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def open_in_editor(file_path: str, editor: str = "zed") -> bool:
    """
    Open a file in the specified editor.

    Args:
        file_path: Path to the file to open
        editor: Editor command (zed, code, vim, nvim, etc.)

    Returns:
        True if editor launched successfully, False otherwise
    """
    path = Path(file_path)

    if not path.exists():
        logger.error(f"File not found: {file_path}")
        return False

    # Check if editor is available
    editor_path = shutil.which(editor)
    if not editor_path:
        logger.error(f"Editor '{editor}' not found in PATH")
        return False

    try:
        # Launch editor (non-blocking)
        subprocess.Popen(
            [editor, str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.info(f"Opened {file_path} in {editor}")
        return True
    except Exception as e:
        logger.error(f"Failed to open editor: {e}")
        return False


def get_editor_display_name(editor: str) -> str:
    """Get a friendly display name for the editor."""
    editor_names = {
        "zed": "Zed",
        "code": "VS Code",
        "vim": "Vim",
        "nvim": "Neovim",
        "nano": "Nano",
        "subl": "Sublime Text",
        "atom": "Atom",
        "emacs": "Emacs",
    }
    return editor_names.get(editor, editor)
