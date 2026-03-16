"""
STARK Folder Manager
─────────────────────
Features:
  - Open any folder by name or path
  - Review all files in folder — give summary
  - Edit / fix / add features to any file
  - Generate new code files in any language
  - Find and open specific files
  - Give full code review for all files in folder
"""

import os
import subprocess
import platform
import json
import datetime


class FolderManager:
    def __init__(self, voice, ask_ai_fn):
        self._voice    = voice
        self._ask_ai   = ask_ai_fn
        self._cwd      = os.path.expanduser("~")
        self._last_reviewed = {}
        print("[STARK FolderMgr] Initialised.")

    # ── Navigate to folder ────────────────────────────────────────────────────
    def open_folder(self, folder_name: str) -> str:
        """Open a folder by name — searches common locations."""
        folder_name = folder_name.strip()

        # Common locations to search
        search_roots = [
            os.path.expanduser("~"),
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.join(os.path.expanduser("~"), "Documents"),
            os.path.join(os.path.expanduser("~"), "Downloads"),
            os.path.join(os.path.expanduser("~"), "OneDrive"),
            os.path.join(os.path.expanduser("~"), "OneDrive", "Documents"),
            "C:\\",
            "D:\\",
        ]

        # Check if it's an exact path first
        if os.path.isdir(folder_name):
            self._cwd = folder_name
            self._open_in_explorer(folder_name)
            self._voice.speak(f"Opened folder: {folder_name}, Sir.")
            return folder_name

        # Search for folder by name
        for root in search_roots:
            if not os.path.exists(root):
                continue
            candidate = os.path.join(root, folder_name)
            if os.path.isdir(candidate):
                self._cwd = candidate
                self._open_in_explorer(candidate)
                self._voice.speak(f"Opened {folder_name} folder, Sir.")
                return candidate

            # Deep search (1 level)
            try:
                for item in os.listdir(root):
                    if item.lower() == folder_name.lower():
                        full = os.path.join(root, item)
                        if os.path.isdir(full):
                            self._cwd = full
                            self._open_in_explorer(full)
                            self._voice.speak(f"Found and opened {folder_name}, Sir.")
                            return full
            except Exception:
                continue

        self._voice.speak(
            f"Sir, I could not find a folder named '{folder_name}'. "
            f"Please give me the full path."
        )
        return ""

    def _open_in_explorer(self, path: str):
        try:
            if platform.system() == "Windows":
                subprocess.Popen(f'explorer "{path}"')
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            print(f"[FolderMgr] {e}")

    # ── Review all files ──────────────────────────────────────────────────────
    def review_folder(self, path: str = "") -> str:
        """Read all code files in folder and give AI review."""
        folder = path or self._cwd
        if not os.path.isdir(folder):
            self._voice.speak(f"Folder not found: {folder}, Sir.")
            return ""

        self._voice.speak(
            f"Reading all files in {os.path.basename(folder)}. "
            f"Please wait Sir, this may take a moment."
        )

        code_extensions = {".py",".js",".ts",".html",".css",".java",".c",
                           ".cpp",".php",".rb",".go",".rs",".jsx",".tsx",
                           ".json",".yaml",".yml",".txt",".md",".sql"}

        all_code = {}
        try:
            for fname in os.listdir(folder):
                fpath = os.path.join(folder, fname)
                ext   = os.path.splitext(fname)[1].lower()
                if os.path.isfile(fpath) and ext in code_extensions:
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        all_code[fname] = content[:3000]  # max 3000 chars per file
                    except Exception:
                        pass
        except Exception as e:
            self._voice.speak(f"Could not read folder, Sir. {e}")
            return ""

        if not all_code:
            self._voice.speak(
                "No code files found in that folder, Sir."
            )
            return ""

        file_list = ", ".join(all_code.keys())
        self._voice.speak(
            f"Found {len(all_code)} files: {file_list}. Reviewing now, Sir."
        )

        # Build review prompt
        code_summary = ""
        for fname, content in all_code.items():
            code_summary += f"\n--- {fname} ---\n{content[:1500]}\n"

        review = self._ask_ai(
            f"Review these code files from the folder '{os.path.basename(folder)}'.\n"
            f"For each file:\n"
            f"1. What it does\n"
            f"2. Any errors or bugs\n"
            f"3. Suggestions to improve\n"
            f"4. Missing features or best practices\n\n"
            f"{code_summary[:5000]}"
        )

        self._voice.speak(review[:600])
        print(f"\n[Code Review — {folder}]\n{'='*50}\n{review}\n{'='*50}\n")
        self._last_reviewed = all_code
        return review

    # ── Fix all errors in folder ──────────────────────────────────────────────
    def fix_folder_errors(self, path: str = "") -> None:
        """Fix errors in all files in folder."""
        folder = path or self._cwd
        if not os.path.isdir(folder):
            self._voice.speak("Folder not found, Sir.")
            return

        code_extensions = {".py",".js",".html",".css",".java",".jsx",".ts"}
        fixed_count = 0

        for fname in os.listdir(folder):
            fpath = os.path.join(folder, fname)
            ext   = os.path.splitext(fname)[1].lower()
            if not os.path.isfile(fpath) or ext not in code_extensions:
                continue

            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                fixed = self._ask_ai(
                    f"Fix ALL bugs and errors in this code. "
                    f"Return ONLY the corrected code:\n\n{content[:4000]}"
                )
                # Strip markdown fences
                if "```" in fixed:
                    fixed = "\n".join(
                        l for l in fixed.splitlines()
                        if not l.strip().startswith("```")
                    )

                # Backup and save
                backup = fpath + ".bak"
                with open(backup, "w", encoding="utf-8") as f:
                    f.write(content)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(fixed)

                fixed_count += 1
                print(f"[Fixed] {fname}")

            except Exception as e:
                print(f"[Fix error] {fname}: {e}")

        self._voice.speak(
            f"Fixed {fixed_count} files in {os.path.basename(folder)}, Sir. "
            f"Originals backed up as .bak files."
        )

    # ── Add feature to file ───────────────────────────────────────────────────
    def add_feature(self, filename: str, feature_description: str,
                    path: str = "") -> None:
        """Ask AI to add a feature to an existing file."""
        folder = path or self._cwd
        fpath  = os.path.join(folder, filename)

        if not os.path.exists(fpath):
            self._voice.speak(f"File {filename} not found, Sir.")
            return

        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            self._voice.speak(
                f"Adding feature to {filename}, Sir. Please wait."
            )

            updated = self._ask_ai(
                f"Add this feature to the existing code: {feature_description}\n\n"
                f"Existing code:\n{content[:4000]}\n\n"
                f"Return the COMPLETE updated code with the new feature added."
            )

            if "```" in updated:
                updated = "\n".join(
                    l for l in updated.splitlines()
                    if not l.strip().startswith("```")
                )

            confirmed = self._voice.confirm(
                f"Sir, I have added the feature. Shall I save {filename}?"
            )
            if confirmed:
                backup = fpath + ".bak"
                with open(backup, "w") as f:
                    f.write(content)
                with open(fpath, "w") as f:
                    f.write(updated)
                self._voice.speak(
                    f"Feature added and saved to {filename}, Sir."
                )
            else:
                print(f"\n[Updated {filename}]\n{updated}\n")
                self._voice.speak("Not saved. Code shown in terminal, Sir.")

        except Exception as e:
            self._voice.speak(f"Error adding feature, Sir: {e}")

    # ── Generate new code file ────────────────────────────────────────────────
    def generate_code_file(self, description: str, filename: str,
                           language: str = "python", path: str = "") -> None:
        """Generate a new code file and save it."""
        folder = path or self._cwd
        fpath  = os.path.join(folder, filename)

        self._voice.speak(
            f"Generating {filename} in {language}, Sir. Please wait."
        )

        code = self._ask_ai(
            f"Write complete, working {language} code for: {description}. "
            f"Return ONLY the code, no explanation, no markdown fences."
        )

        if "```" in code:
            code = "\n".join(
                l for l in code.splitlines()
                if not l.strip().startswith("```")
            )

        confirmed = self._voice.confirm(
            f"Sir, I have generated {filename}. Shall I save it to {folder}?"
        )
        if confirmed:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(code)
            self._voice.speak(
                f"{filename} saved successfully to {folder}, Sir."
            )
            # Open in VS Code
            try:
                subprocess.Popen(["code", fpath])
            except Exception:
                pass
        else:
            print(f"\n[Generated Code — {filename}]\n{code}\n")
            self._voice.speak("Code shown in terminal, Sir.")

    # ── List folder contents ──────────────────────────────────────────────────
    def list_folder(self, path: str = "") -> str:
        folder = path or self._cwd
        try:
            items   = os.listdir(folder)
            folders = [i for i in items if os.path.isdir(os.path.join(folder, i))]
            files   = [i for i in items if os.path.isfile(os.path.join(folder, i))]

            msg = (f"In {os.path.basename(folder)}, Sir: "
                   f"{len(folders)} folders and {len(files)} files. "
                   f"Files: {', '.join(files[:8])}")

            self._voice.speak(msg)
            print(f"\n[Folder: {folder}]")
            for f in sorted(files): print(f"  📄 {f}")
            for f in sorted(folders): print(f"  📁 {f}")
            return msg
        except Exception as e:
            self._voice.speak(f"Could not read folder, Sir: {e}")
            return ""

    @property
    def current_path(self) -> str:
        return self._cwd