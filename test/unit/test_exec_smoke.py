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

