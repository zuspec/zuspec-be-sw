#****************************************************************************
# Copyright 2019-2025 Matthew Ballance and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#****************************************************************************
"""
Output file management utilities.
"""
import os
from pathlib import Path
from typing import Dict, List, Optional


class OutputFile:
    """Represents a generated output file."""

    def __init__(self, path: Path, content: str):
        self.path = path
        self.content = content

    def write(self):
        """Write the file to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.content)


class OutputManager:
    """Manages generated output files."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.files: Dict[str, OutputFile] = {}

    def add_file(self, name: str, content: str) -> Path:
        """Add a generated file."""
        path = self.output_dir / name
        self.files[name] = OutputFile(path, content)
        return path

    def add_header(self, name: str, content: str) -> Path:
        """Add a header file."""
        return self.add_file(f"{name}.h", content)

    def add_source(self, name: str, content: str) -> Path:
        """Add a source file."""
        return self.add_file(f"{name}.c", content)

    def write_all(self) -> List[Path]:
        """Write all files to disk and return paths."""
        paths = []
        for f in self.files.values():
            f.write()
            paths.append(f.path)
        return paths

    def get_sources(self) -> List[Path]:
        """Get list of source file paths."""
        return [f.path for name, f in self.files.items() if name.endswith(".c")]

    def get_headers(self) -> List[Path]:
        """Get list of header file paths."""
        return [f.path for name, f in self.files.items() if name.endswith(".h")]
