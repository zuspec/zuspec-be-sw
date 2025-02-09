#****************************************************************************
#* setup.py for zuspec-be-sw
#****************************************************************************
import os
import sys
from setuptools import Extension, find_namespace_packages

proj_dir = os.path.dirname(os.path.abspath(__file__))

try:
    sys.path.insert(0, os.path.join(proj_dir, "python/zsp_be_sw"))
    from __version__ import VERSION, BASE
    base=BASE
    version=VERSION
except ImportError as e:
    print("Import error: %s" % str(e))
    base="0.0.1"
    version=base

isSrcBuild = False

try:
    from ivpm.setup import setup
    isSrcBuild = os.path.isdir(os.path.join(proj_dir, "src"))
    print("zuspec-be-sw: running IVPM SrcBuild")
except ImportError as e:
    from setuptools import setup
    print("zuspec-be-sw: running non-src build")

ext = Extension("zsp_be_sw.core",
            sources=[
                os.path.join(proj_dir, 'python', "core.pyx"), 
            ],
            language="c++",
            include_dirs=[
                os.path.join(proj_dir, 'python'),
                os.path.join(proj_dir, 'src', 'include'),
                # os.path.join(packages_dir, 'ciostream', 'src', 'ciostream'),
                # os.path.join(packages_dir, 'zuspec-arl-dm', 'src', 'include'),
                # os.path.join(packages_dir, 'zuspec-arl-dm', 'python'),
                # os.path.join(packages_dir, 'vsc-dm', 'src', 'include'),
                # os.path.join(packages_dir, 'vsc-dm', 'python'),
                # os.path.join(packages_dir, 'debug-mgr', 'src', 'include'),
                # os.path.join(packages_dir, 'debug-mgr', 'python'),
            ]
        )
ext.cython_directives={'language_level' : '3'}

setup_args = dict(
  name = "zuspec-be-sw",
  version=version,
  packages=['zsp_be_sw'],
  package_dir = {'' : 'python'},
  author = "Matthew Ballance",
  author_email = "matt.ballance@gmail.com",
  description = ("Backend library to generate software output"),
  long_description = """
  Provides features for mapping ARL models to software output
  """,
  license = "Apache 2.0",
  keywords = ["SystemVerilog", "Verilog", "RTL", "Python"],
  url = "https://github.com/zuspec/zuspec-be-sw",
  install_requires=[
    'ciostream',
    'zuspec-arl-dm>=%s' % base,
    'vsc-dm',
    'debug-mgr'
  ],
  setup_requires=[
    'cython',
    'setuptools_scm',
  ],
  ext_modules=[ ext ]
)

if isSrcBuild:
    setup_args["ivpm_extdep_pkgs"] = [
        "ciostream",
        "zuspec-arl-dm",
        "vsc-dm",
        "debug-mgr"]
    setup_args["ivpm_extra_data"] = {
        "zsp_be_sw": [
            ("src/include", "share"),
            ("build/{libdir}/{libpref}zsp-be-sw{dllext}", ""),
        ]
    }

setup(**setup_args)

