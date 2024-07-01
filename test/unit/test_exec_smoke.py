import io
import os
from .test_base import TestBase

class TestExecSmoke(TestBase):

    def test_smoke(self):
        content = """
        // import std_pkg::*;

        import function void print(string msg);

        component base_t {
            int a;
            /*
            exec init_down {
                print("Hello");
            }

            exec init_up {
                print("Hello");
            }
             */
        }

        component pss_top : base_t {
            int         a;
            int         b;
            base_t      c;

            /*
            exec init_down {
                int i;
                i = 1;
                i = a;
                if (a == 5) {
                    i = 2;
                } else if (a == 6) {
                    i = 3;
                } else {
                    i = 4;
                }

                if (a == 2) {
                    i = 1;
                }
            }

            exec init_up {
            }
             */

            action Sub {
                exec pre_solve {
                    print("Hello from Sub");
                }
                exec body {
                    // TODO:
                    print("Hello from body");
                }
            }

            action Entry {
                int a;
                exec pre_solve {
                    print("Hello from Smoke Test");
                }
                activity {
                    do Sub;
                }
            }
        }
        """

        self.genBuildRun(
            content,
            "pss_top",
            "pss_top::Entry",
            extra_src=[
                os.path.join(self.data_dir, "support/support.c")
            ],
            extra_hdr=[
                os.path.join(self.data_dir, "support/support.h")
            ]
        )

    def test_reg_smoke(self):
        content = """
        import addr_reg_pkg::*;
        import function void print(string msg);

        pure component my_regs : reg_group_c {
            reg_c<bit[32]>      r1;
            reg_c<bit[32]>      r2;
        }

        component pss_top {
            my_regs     regs;
            ref my_regs     regs_p;

            exec init_down {
            }

            action Entry {
                int a;
                exec body {
                    print("Hello from Smoke Test");
                    comp.regs.r2.write_val(0);
                }
            }
        }
        """

        self.genBuildRun(
            content,
            "pss_top",
            "pss_top::Entry",
            extra_src=[
                os.path.join(self.data_dir, "support/support.c")
            ],
            extra_hdr=[
                os.path.join(self.data_dir, "support/support.h")
            ]
        )

    def test_reg_set_handle(self):
        content = """
        import addr_reg_pkg::*;
        import function void print(string msg);

        pure component my_regs : reg_group_c {
            reg_c<bit[32]>      r1;
            reg_c<bit[32]>      r2;
        }

        component pss_top {
            transparent_addr_space_c<>  aspace;
            my_regs                     regs;

            exec init_down {
                transparent_addr_region_s<> region;
                addr_handle_t hndl;

                region.addr = 0x80000000;

                hndl = aspace.add_nonallocatable_region(region);
                regs.set_handle(hndl);
            }

            action Entry {
                int a;
                exec body {
                    print("Hello from Smoke Test");
                    comp.regs.r2.write_val(0);
                }
            }
        }
        """

        self.genBuildRun(
            content,
            "pss_top",
            "pss_top::Entry",
            extra_src=[
                os.path.join(self.data_dir, "support/support.c")
            ],
            extra_hdr=[
                os.path.join(self.data_dir, "support/support.h")
            ]
        )