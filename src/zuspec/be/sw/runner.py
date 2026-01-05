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
Test runner for executing compiled C code.
"""
import subprocess
from pathlib import Path
from typing import Optional


class TestResult:
    """Result of running a test executable."""
    def __init__(self, passed: bool, stdout: str = "", stderr: str = "", 
                 return_code: int = 0):
        self.passed = passed
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code


class TestRunner:
    """Runs compiled test executables and validates output."""

    def run(self, executable: Path, 
            expected_output: Optional[str] = None,
            expected_return: int = 0,
            timeout: int = 30) -> TestResult:
        """
        Run an executable and check the result.
        
        Args:
            executable: Path to the executable
            expected_output: String that should be in stdout (if any)
            expected_return: Expected return code
            timeout: Maximum execution time in seconds
        
        Returns:
            TestResult with pass/fail status and output
        """
        try:
            result = subprocess.run(
                [str(executable)],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            passed = result.returncode == expected_return
            
            if expected_output and passed:
                passed = expected_output in result.stdout
            
            return TestResult(
                passed=passed,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                passed=False,
                stderr=f"Execution timed out after {timeout} seconds"
            )
        except Exception as e:
            return TestResult(
                passed=False,
                stderr=str(e)
            )
