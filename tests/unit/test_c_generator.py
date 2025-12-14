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
Unit tests for the c_generator module.
"""
import tempfile
from pathlib import Path
import pytest
import zuspec.dataclasses as zdc

from zuspec.be.sw.c_generator import CGenerator, sanitize_c_name


class TestSanitizeCName:
    """Tests for sanitize_c_name function."""

    def test_simple_name(self):
        """Test that simple names are unchanged."""
        assert sanitize_c_name("MyClass") == "MyClass"

    def test_qualified_name(self):
        """Test that qualified names extract last part."""
        assert sanitize_c_name("test_func.<locals>.MyClass") == "MyClass"

    def test_name_with_dots(self):
        """Test name with multiple dots."""
        assert sanitize_c_name("a.b.c.MyClass") == "MyClass"

    def test_name_with_invalid_chars(self):
        """Test that invalid characters are replaced."""
        assert sanitize_c_name("My-Class") == "My_Class"
        assert sanitize_c_name("My Class") == "My_Class"

    def test_name_starting_with_digit(self):
        """Test that names starting with digits get prefix."""
        assert sanitize_c_name("123Class") == "_123Class"

    def test_empty_name(self):
        """Test empty name."""
        assert sanitize_c_name("") == ""


# Define components at module level so inspect.getsource() can find them
@zdc.dataclass
class GenTestComp(zdc.Component):
    def test_method(self):
        pass


@zdc.dataclass
class GenHeaderTestComp(zdc.Component):
    pass


@zdc.dataclass
class GenPrintTestComp(zdc.Component):
    def say_hello(self):
        print("Hello World")


class TestCGenerator:
    """Tests for CGenerator class."""

    def test_generate_creates_files(self, tmpdir):
        """Test that generate creates output files."""
        dm_ctxt = zdc.DataModelFactory().build(GenTestComp)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        assert len(sources) > 0
        # Check that files were created
        for src in sources:
            assert src.exists()

    def test_generate_header_includes_guard(self, tmpdir):
        """Test that generated header has include guard."""
        dm_ctxt = zdc.DataModelFactory().build(GenHeaderTestComp)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Find header file
        header_files = [s for s in sources if s.suffix == '.h']
        assert len(header_files) > 0
        
        header = header_files[0].read_text()
        assert '#ifndef' in header
        assert '#define' in header
        assert '#endif' in header

    def test_generate_includes_zsp_component(self, tmpdir):
        """Test that generated header includes zsp_component.h."""
        dm_ctxt = zdc.DataModelFactory().build(GenHeaderTestComp)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Find header file
        header_files = [s for s in sources if s.suffix == '.h']
        header = header_files[0].read_text()
        assert '#include "zsp_component.h"' in header

    def test_generate_creates_main(self, tmpdir):
        """Test that generate creates main.c."""
        dm_ctxt = zdc.DataModelFactory().build(GenHeaderTestComp)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        main_files = [s for s in sources if s.name == 'main.c']
        assert len(main_files) == 1
        
        main = main_files[0].read_text()
        assert 'int main(' in main

    def test_generate_method_with_print(self, tmpdir):
        """Test that print statement is converted to fprintf."""
        dm_ctxt = zdc.DataModelFactory().build(GenPrintTestComp)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Find source file (not main.c)
        src_files = [s for s in sources if s.suffix == '.c' and s.name != 'main.c']
        assert len(src_files) > 0
        
        src = src_files[0].read_text()
        assert 'fprintf' in src
        assert 'Hello World' in src
