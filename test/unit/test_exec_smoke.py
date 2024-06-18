import io
from .test_base import TestBase

class TestExecSmoke(TestBase):

    def test_smoke(self):
        content = """
        component base_t {
            int a;
        }
        component pss_top : base_t {
            int         a;
            int         b;
            base_t      c;

            exec init_down {
                int i;
                i = 1;
                i = a;
            }

            action Entry {
                exec pre_solve {
//                    print("Hello from Smoke Test");
                }
            }
        }
        """

        arl_ctxt, comp_t, action_t = self.buildModelGetRoots(
            content,
            "pss_top",
            "pss_top::Entry"
        )

        c_out = io.StringIO()
        h_out = io.StringIO()
        h_prv_out = io.StringIO()

        self.be_sw_f.generateExecModel(
            arl_ctxt,
            comp_t,
            action_t,
            c_out,
            h_out,
            h_prv_out
        )

        print("c_out:\n%s" % c_out.getvalue())
        print("h_out:\n%s" % h_out.getvalue())
        print("h_prv_out:\n%s" % h_prv_out.getvalue())
