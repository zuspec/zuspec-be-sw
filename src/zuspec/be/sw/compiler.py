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
C compiler wrapper for compiling generated code.
"""
import os
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional


class CompileResult:
    """Result of a compilation attempt."""
    def __init__(self, success: bool, stdout: str = "", stderr: str = ""):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr


class CCompiler:
    """Compiles C source files with the ZSP runtime."""

    # Runtime source files needed for compilation
    RT_SOURCES = [
        "zsp_alloc.c",
        "zsp_timebase.c",
        "zsp_thread.c",
        "zsp_list.c",
        "zsp_object.c",
        "zsp_component.c",
        "zsp_struct.c",
        "zsp_map.c",
    ]

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.share_dir = self._find_share_dir()
        self.rt_dir = self.share_dir / "rt"
        self.include_dir = self.share_dir / "include"

    def _find_share_dir(self) -> Path:
        """Find the share directory with runtime sources."""
        # Relative to this module
        module_dir = Path(__file__).parent
        share_dir = module_dir / "share"
        if share_dir.exists():
            return share_dir
        
        # Try from repo root
        repo_root = module_dir.parent.parent.parent.parent
        share_dir = repo_root / "src" / "zuspec" / "be" / "sw" / "share"
        if share_dir.exists():
            return share_dir
        
        raise RuntimeError("Could not find share directory with runtime sources")

    def get_runtime_sources(self) -> List[Path]:
        """Get list of runtime source files."""
        return [self.rt_dir / src for src in self.RT_SOURCES if (self.rt_dir / src).exists()]

    def compile(self, sources: List[Path], output: Path, 
                extra_includes: Optional[List[Path]] = None) -> CompileResult:
        """Compile C sources to executable."""
        # Find compiler
        cc = self._find_compiler()
        if cc is None:
            return CompileResult(False, stderr="No C compiler found (tried gcc, clang)")

        # Build command
        cmd = [
            cc, "-g", "-O0",
            f"-I{self.include_dir}",
            "-o", str(output),
        ]
        
        # Add extra includes
        if extra_includes:
            for inc in extra_includes:
                cmd.append(f"-I{inc}")
        
        # Add generated sources
        cmd.extend(str(s) for s in sources)
        
        # Add runtime sources
        cmd.extend(str(s) for s in self.get_runtime_sources())

        # Run compiler
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.output_dir)
        )

        return CompileResult(
            success=(result.returncode == 0),
            stdout=result.stdout,
            stderr=result.stderr
        )

    def compile_shared(self, sources: List[Path], output: Path,
                      extra_includes: Optional[List[Path]] = None) -> CompileResult:
        """Compile C sources to shared library.
        
        Args:
            sources: List of C source files to compile
            output: Output .so file path
            extra_includes: Additional include directories
            
        Returns:
            CompileResult with success status and output
        """
        cc = self._find_compiler()
        if cc is None:
            return CompileResult(False, stderr="No C compiler found (tried gcc, clang)")
        
        # Build command for shared library
        cmd = [
            cc, "-g", "-O2", "-fPIC", "-shared",
            "-Wno-error",  # Don't treat warnings as errors
            f"-I{self.include_dir}",
            "-o", str(output),
        ]
        
        # Add extra includes
        if extra_includes:
            for inc in extra_includes:
                cmd.append(f"-I{inc}")
        
        # Add generated sources
        cmd.extend(str(s) for s in sources)
        
        # Add runtime sources
        cmd.extend(str(s) for s in self.get_runtime_sources())
        
        # Run compiler
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.output_dir)
        )
        
        return CompileResult(
            success=(result.returncode == 0),
            stdout=result.stdout,
            stderr=result.stderr
        )

    def _find_compiler(self) -> Optional[str]:
        """Find available C compiler."""
        for compiler in ["gcc", "clang", "cc"]:
            if shutil.which(compiler):
                return compiler
        return None
