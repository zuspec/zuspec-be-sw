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
ZuSpec Backend for SW (C) code generation.
"""
import zuspec.dataclasses as zdc

from .c_generator import CGenerator
from .validator import CValidator, ValidationError
from .compiler import CCompiler, CompileResult
from .runner import TestRunner, TestResult
from .type_mapper import TypeMapper
from .stmt_generator import StmtGenerator
from .dm_async_generator import DmAsyncMethodGenerator
from .output import OutputManager, OutputFile

__all__ = [
    "CGenerator",
    "CValidator",
    "ValidationError",
    "CCompiler",
    "CompileResult",
    "TestRunner",
    "TestResult",
    "TypeMapper",
    "StmtGenerator",
    "DmAsyncMethodGenerator",
    "OutputManager",
    "OutputFile",
]
