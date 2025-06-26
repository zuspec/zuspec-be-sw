import os

def lib_rt():
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.abspath(os.path.join(pkg_dir, "../../build"))

    lib = None
    if os.path.isfile(os.path.join(pkg_dir, "libzsp-be-sw-rt.so")):
        lib = os.path.join(build_dir, "libzsp-be-sw-rt.so")
    else:
        for l in ("lib", "lib64"):
            if os.path.isfile(os.path.join(build_dir, l, "libzsp-be-sw-rt.so")):
                lib = os.path.join(build_dir, l, "libzsp-be-sw-rt.so")
                break
    return lib

