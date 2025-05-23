#include <stdio.h>

typedef struct pss_top_Entry_s {
    int idx;
    int i;
    int x;

} pss_top_Entry_t;

void pss_top_Entry_body(pss_top_Entry_t *ctxt) {
    switch (ctxt->idx) {
        case 0: {
            ctxt->idx = 1;
__line__007:
            ctxt->i = 2;
__line__008:
            ctxt->x = 3;
        }
        case 1: {
__line__009:
            fprintf(stdout, "i\n");
__line__010:
            fprintf(stdout, "x\n");
        }
    }
}

void pss_top_Entry() {
    pss_top_Entry_t     ctxt;

line_7:
    pss_top_Entry_body(&ctxt);
}

int main() {
    pss_top_Entry();
}