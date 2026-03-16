"""
STARK File Explorer Module
  - Browse folders and files
  - Read file content
  - Edit / add / delete lines in code files
  - Create new files
  - Delete files (with confirmation)
  - Open files in default editor
  - Find files by name
  - All edits require Sir's confirmation
"""

import os
import shutil
import subprocess
import platform
import config


SAFE_EXTENSIONS = (
    ".py", ".js", ".ts", ".html", ".css", ".json",
    ".txt", ".md", ".java", ".c", ".cpp", ".h",
    ".jsx", ".tsx", ".php", ".rb", ".go", ".rs",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env",
    ".sql", ".sh", ".bat", ".xml", ".csv",
)


class FileExplorerModule:
    def __init__(self, voice, ai_brain_ask_fn):
        """
        voice         : VoiceModule instance
        ai_brain_ask_fn : reference to AIBrain._ask_ai()  (for code AI analysis)
        """
        self._voice  = voice
        self._ask_ai = ai_brain_ask_fn
        self._cwd    = os.path.expanduser("~")   # start at home dir
        print("[STARK FileExplorer] Initialised.")
        print(f"[STARK FileExplorer] Current directory: {self._cwd}")

    # ══════════════════════════════════════════════════════════════════════════
    # Navigation
    # ══════════════════════════════════════════════════════════════════════════

    def list_directory(self, path: str = "") -> str:
        """List files and folders in current or given path."""
        target = path or self._cwd
        try:
            items = os.listdir(target)
            folders = [i for i in items if os.path.isdir(os.path.join(target, i))]
            files   = [i for i in items if os.path.isfile(os.path.join(target, i))]

            result = f"Location: {target}\n"
            result += f"Folders ({len(folders)}): {', '.join(folders[:10]) or 'none'}\n"
            result += f"Files ({len(files)}): {', '.join(files[:15]) or 'none'}"

            self._voice.speak(
                f"Sir, in {os.path.basename(target)}, "
                f"there are {len(folders)} folders and {len(files)} files."
            )
            print(result)
            return result
        except Exception as e:
            self._voice.speak(f"Could not list that directory, Sir. {e}")
            return ""

    def change_directory(self, path: str) -> None:
        """Change current working directory."""
        if path == "..":
            self._cwd = os.path.dirname(self._cwd)
        elif os.path.isabs(path):
            self._cwd = path
        else:
            self._cwd = os.path.join(self._cwd, path)

        if os.path.isdir(self._cwd):
            self._voice.speak(f"Moved to {self._cwd}, Sir.")
            self.list_directory()
        else:
            self._voice.speak(f"That folder does not exist, Sir.")
            self._cwd = os.path.expanduser("~")

    def go_to_desktop(self) -> None:
        self.change_directory(os.path.join(os.path.expanduser("~"), "Desktop"))

    def go_to_downloads(self) -> None:
        self.change_directory(os.path.join(os.path.expanduser("~"), "Downloads"))

    def go_to_documents(self) -> None:
        self.change_directory(os.path.join(os.path.expanduser("~"), "Documents"))

    # ══════════════════════════════════════════════════════════════════════════
    # Read Files
    # ══════════════════════════════════════════════════════════════════════════

    def read_file(self, filename: str) -> str:
        """Read and return the content of a file."""
        filepath = self._resolve(filename)
        if not filepath:
            return ""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            lines = content.splitlines()
            self._voice.speak(
                f"Sir, {filename} has {len(lines)} lines. Reading it now."
            )
            print(f"\n{'─'*50}\n{content}\n{'─'*50}")
            return content
        except Exception as e:
            self._voice.speak(f"Could not read {filename}, Sir. {e}")
            return ""

    def read_and_speak_file(self, filename: str) -> None:
        """Read a file and speak the first portion aloud."""
        content = self.read_file(filename)
        if content:
            # Speak first ~300 chars
            preview = content[:300].replace("\n", " ").strip()
            self._voice.speak(preview)

    # ══════════════════════════════════════════════════════════════════════════
    # Code Analysis (AI-powered)
    # ══════════════════════════════════════════════════════════════════════════

    def check_file_for_errors(self, filename: str) -> None:
        """Read a code file and ask AI to find errors."""
        content = self.read_file(filename)
        if not content:
            return

        self._voice.speak(f"Analysing {filename} for errors, Sir. Please wait.")
        answer = self._ask_ai(
            f"Review this code and find any bugs, errors, or improvements. "
            f"Be specific about line numbers if possible. File: {filename}\n\n"
            f"{content[:4000]}"
        )
        self._voice.speak(answer)
        print(f"\n[STARK Code Review]\n{answer}\n")

    def explain_file(self, filename: str) -> None:
        """Ask AI to explain what a code file does."""
        content = self.read_file(filename)
        if not content:
            return

        self._voice.speak(f"Let me explain {filename} for you, Sir.")
        answer = self._ask_ai(
            f"Explain what this code does in simple terms:\n\n{content[:4000]}"
        )
        self._voice.speak(answer)

    # ══════════════════════════════════════════════════════════════════════════
    # Edit Files
    # ══════════════════════════════════════════════════════════════════════════

    def edit_line(self, filename: str, line_number: int, new_content: str) -> None:
        """Replace a specific line in a file."""
        filepath = self._resolve(filename)
        if not filepath:
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if line_number < 1 or line_number > len(lines):
                self._voice.speak(
                    f"Sir, line {line_number} does not exist in {filename}."
                )
                return

            old = lines[line_number - 1].rstrip()
            confirmed = self._voice.confirm(
                f"Sir, line {line_number} currently says: {old[:80]}. "
                f"Shall I replace it with: {new_content[:80]}?"
            )
            if not confirmed:
                self._voice.speak("Edit cancelled, Sir.")
                return

            lines[line_number - 1] = new_content + "\n"
            self._write_file(filepath, "".join(lines))
            self._voice.speak(f"Line {line_number} updated in {filename}, Sir.")

        except Exception as e:
            self._voice.speak(f"Edit failed, Sir. {e}")

    def add_line(self, filename: str, content: str, after_line: int = None) -> None:
        """Add a new line to a file (at end or after a specific line)."""
        filepath = self._resolve(filename)
        if not filepath:
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            position = after_line if after_line else len(lines)
            confirmed = self._voice.confirm(
                f"Sir, shall I add '{content[:80]}' "
                f"{'after line ' + str(after_line) if after_line else 'at the end'} "
                f"of {filename}?"
            )
            if not confirmed:
                self._voice.speak("Cancelled, Sir.")
                return

            lines.insert(position, content + "\n")
            self._write_file(filepath, "".join(lines))
            self._voice.speak(f"Line added to {filename}, Sir.")

        except Exception as e:
            self._voice.speak(f"Could not add line, Sir. {e}")

    def delete_line(self, filename: str, line_number: int) -> None:
        """Delete a specific line from a file."""
        filepath = self._resolve(filename)
        if not filepath:
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if line_number < 1 or line_number > len(lines):
                self._voice.speak(
                    f"Line {line_number} does not exist in {filename}, Sir."
                )
                return

            old = lines[line_number - 1].rstrip()
            confirmed = self._voice.confirm(
                f"Sir, shall I delete line {line_number}: {old[:80]}?"
            )
            if not confirmed:
                self._voice.speak("Deletion cancelled, Sir.")
                return

            del lines[line_number - 1]
            self._write_file(filepath, "".join(lines))
            self._voice.speak(f"Line {line_number} deleted from {filename}, Sir.")

        except Exception as e:
            self._voice.speak(f"Could not delete line, Sir. {e}")

    def find_and_replace(self, filename: str, find_text: str, replace_text: str) -> None:
        """Find and replace text throughout a file."""
        filepath = self._resolve(filename)
        if not filepath:
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            count = content.count(find_text)
            if count == 0:
                self._voice.speak(
                    f"Sir, I couldn't find '{find_text}' in {filename}."
                )
                return

            confirmed = self._voice.confirm(
                f"Sir, I found '{find_text}' {count} time(s) in {filename}. "
                f"Shall I replace all with '{replace_text}'?"
            )
            if not confirmed:
                self._voice.speak("Replacement cancelled, Sir.")
                return

            new_content = content.replace(find_text, replace_text)
            self._write_file(filepath, new_content)
            self._voice.speak(
                f"Done, Sir. Replaced {count} occurrence(s) in {filename}."
            )

        except Exception as e:
            self._voice.speak(f"Find and replace failed, Sir. {e}")

    def ai_fix_file(self, filename: str) -> None:
        """Let AI read the file, fix all errors, and write the corrected version."""
        content = self.read_file(filename)
        if not content:
            return

        self._voice.speak(
            f"Sir, I'm going to ask my AI to fix all errors in {filename}. "
            f"One moment please."
        )
        fixed = self._ask_ai(
            f"Fix ALL bugs and errors in this code. "
            f"Return ONLY the corrected complete code, nothing else:\n\n{content[:4000]}"
        )

        # Strip markdown fences if AI added them
        if fixed.startswith("```"):
            lines = fixed.splitlines()
            lines = [l for l in lines if not l.strip().startswith("```")]
            fixed = "\n".join(lines)

        confirmed = self._voice.confirm(
            f"Sir, I have the corrected version of {filename}. "
            f"Shall I save it? The original will be backed up."
        )
        if not confirmed:
            self._voice.speak("File not changed, Sir.")
            print(f"\n[STARK Fixed Code]\n{fixed}\n")
            return

        # Backup original
        backup = self._resolve(filename) + ".bak"
        shutil.copy2(self._resolve(filename), backup)

        self._write_file(self._resolve(filename), fixed)
        self._voice.speak(
            f"File fixed and saved, Sir. Original backed up as {os.path.basename(backup)}."
        )

    # ══════════════════════════════════════════════════════════════════════════
    # Create / Delete Files
    # ══════════════════════════════════════════════════════════════════════════

    def create_file(self, filename: str, content: str = "") -> None:
        """Create a new file with optional content."""
        filepath = os.path.join(self._cwd, filename)

        if os.path.exists(filepath):
            confirmed = self._voice.confirm(
                f"Sir, {filename} already exists. Shall I overwrite it?"
            )
            if not confirmed:
                self._voice.speak("File creation cancelled, Sir.")
                return

        confirmed = self._voice.confirm(
            f"Sir, shall I create {filename} in {self._cwd}?"
        )
        if not confirmed:
            self._voice.speak("Cancelled, Sir.")
            return

        self._write_file(filepath, content)
        self._voice.speak(f"{filename} created successfully, Sir.")

    def delete_file(self, filename: str) -> None:
        """Delete a file (with confirmation)."""
        filepath = self._resolve(filename)
        if not filepath:
            return

        confirmed = self._voice.confirm(
            f"Sir, are you sure you want to permanently delete {filename}? "
            f"This cannot be undone."
        )
        if not confirmed:
            self._voice.speak("Deletion cancelled, Sir.")
            return

        try:
            os.remove(filepath)
            self._voice.speak(f"{filename} has been deleted, Sir.")
        except Exception as e:
            self._voice.speak(f"Could not delete {filename}, Sir. {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # Open Files
    # ══════════════════════════════════════════════════════════════════════════

    def open_file(self, filename: str) -> None:
        """Open a file in the default system application."""
        filepath = self._resolve(filename)
        if not filepath:
            return

        try:
            if platform.system() == "Windows":
                os.startfile(filepath)
            elif platform.system() == "Darwin":
                subprocess.call(["open", filepath])
            else:
                subprocess.call(["xdg-open", filepath])
            self._voice.speak(f"Opening {filename}, Sir.")
        except Exception as e:
            self._voice.speak(f"Could not open {filename}, Sir. {e}")

    def open_in_vscode(self, filename: str) -> None:
        """Open a file or folder in VS Code."""
        filepath = self._resolve(filename) or self._cwd
        try:
            subprocess.Popen(["code", filepath])
            self._voice.speak(f"Opening {filename or 'folder'} in VS Code, Sir.")
        except FileNotFoundError:
            self._voice.speak(
                "VS Code is not installed or not in PATH, Sir. "
                "Please install it from code.visualstudio.com"
            )

    # ══════════════════════════════════════════════════════════════════════════
    # Find Files
    # ══════════════════════════════════════════════════════════════════════════

    def find_file(self, name: str, search_root: str = "") -> list:
        """Search for files matching a name pattern."""
        root = search_root or self._cwd
        matches = []
        self._voice.speak(f"Searching for {name}, Sir. Please wait.")

        for dirpath, dirnames, filenames in os.walk(root):
            # Skip hidden folders
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for f in filenames:
                if name.lower() in f.lower():
                    matches.append(os.path.join(dirpath, f))
            if len(matches) >= 20:
                break

        if matches:
            self._voice.speak(
                f"Sir, I found {len(matches)} file(s) matching {name}."
            )
            for m in matches[:5]:
                print(f"  → {m}")
        else:
            self._voice.speak(f"No files matching {name} found, Sir.")

        return matches

    # ══════════════════════════════════════════════════════════════════════════
    # Generate and Save Code (AI-powered)
    # ══════════════════════════════════════════════════════════════════════════

    def generate_and_save(self, description: str, filename: str) -> None:
        """Ask AI to generate code and save it to a file."""
        self._voice.speak(
            f"Generating {filename} for you, Sir. Please wait."
        )
        code = self._ask_ai(
            f"Write complete, working code for: {description}. "
            f"Return ONLY the code, no explanation, no markdown fences."
        )

        # Clean markdown
        if "```" in code:
            lines = code.splitlines()
            lines = [l for l in lines if not l.strip().startswith("```")]
            code = "\n".join(lines)

        confirmed = self._voice.confirm(
            f"Sir, I've generated {filename}. Shall I save it to {self._cwd}?"
        )
        if not confirmed:
            self._voice.speak("Not saved, Sir. Here is the code in the console.")
            print(code)
            return

        filepath = os.path.join(self._cwd, filename)
        self._write_file(filepath, code)
        self._voice.speak(f"{filename} saved successfully, Sir.")

    # ══════════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _resolve(self, filename: str) -> str:
        """Resolve a filename to full path. Returns '' if not found."""
        if os.path.isabs(filename) and os.path.exists(filename):
            return filename

        # Check current directory
        candidate = os.path.join(self._cwd, filename)
        if os.path.exists(candidate):
            return candidate

        self._voice.speak(
            f"Sir, I could not find {filename} in {self._cwd}. "
            f"Please check the file name."
        )
        return ""

    def _write_file(self, filepath: str, content: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def current_path(self) -> str:
        return self._cwd
