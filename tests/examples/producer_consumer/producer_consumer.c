#include <stdint.h>
#include <stdio.h>


typedef struct comp_base_s {

} comp_base_t;

typedef struct pss_top_s {
    comp_base_t         base;

} pss_top_t;


struct obj_base_s;

typedef struct vtab_base_s {
    void (*dtor)(struct obj_base_s *);
    void (*randomize)(struct obj_base_s *);
} vtab_base_t;

typedef struct obj_base_s {
    vtab_base_t         *vtable;
} obj_base_t;

typedef struct data_s {
    obj_base_t          base;

} data_t;

typedef struct task_s {
    int (*entry)(struct task_s *);
    struct task_s       *next;
} task_t;

typedef struct actor_s {
    task_t          *callstack;
    task_t          *runnable;
} actor_t;

typedef struct obj_handle_s {

} obj_handle_t;

typedef struct action_base_s {
    obj_base_t          base;
    int32_t             step;
    comp_base_t         *comp;
} action_base_t;

typedef struct pss_top_Producer_s {
    action_base_t        base;
    data_t               *dat_o;
} pss_top_Producer_t;

typedef struct pss_top_Consumer_s {
    action_base_t        base;
    data_t               *dat_i;
    data_t               *dat_o;
} pss_top_Consumer_t;

typedef struct pss_top_Entry_s {
    action_base_t        base;
    pss_top_Producer_t   *repeat_P;
    data_t               *repeat_P_dat_o;
    pss_top_Consumer_t   *repeat_C;
} pss_top_Entry_t;

int pss_top_Producer_body(pss_top_Producer_t *ctxt) {
    int ret = 0;
    switch (ctxt->base.step) {
        case 0: {
            ctxt->base.step = 1;
            // Perform randomization

        }
        case 1: { // Body
            ctxt->base.step = 2;
        }
    }
    return ret;
}

void pss_top_Producer_dtor(pss_top_Producer_t *ctxt) {
    if (ctxt->dat_o) {
        ctxt->dat_o->base.vtable->dtor(&ctxt->dat_o->base);
    }
}

void pss_top_Producer_rand(pss_top_Producer_t *ctxt) {
    // 
}

static vtab_base_t pss_top_Producer_vtab = {
    .randomize = (void (*)(obj_base_t *))&pss_top_Producer_rand,
    .dtor = (void (*)(obj_base_t *))&pss_top_Producer_dtor
};

pss_top_Producer_t *pss_top_Producer_ctor(pss_top_t *ctxt) {
    pss_top_Producer_t *ret;

    ret->base.base.vtable = &pss_top_Producer_vtab;

    return ret;
}


int pss_top_Consumer_body(pss_top_Consumer_t *ctxt) {


}

pss_top_Consumer_t *pss_top_Consumer_ctor(
    pss_top_t           *ctxt,
    data_t              *dat_i) {
    pss_top_Consumer_t *ret;

    ret->dat_i = dat_i;

    return ret;
}

pss_top_Entry_t *pss_top_Entry_ctor(pss_top_t *ctxt) {
    pss_top_Entry_t *ret = 0;
    ret->base.comp = &ctxt->base;

    return ret;
}

int pss_top_Entry_body(
    pss_top_Entry_t         *ctxt,
    task_t                  **tasklist) {
    int ret = 0;

    switch (ctxt->base.step) {
        case 0: {
            ctxt->base.step = 1;
            // Randomize

            // Add this task to the tasklist
        }
        case 1: {
            // Body
            // Push context
            ctxt->base.step = 2;

            // if (!pss_top_Entry_body_XXX()) {
            //     // Pop context
            // } else {
            //     ret = 1;
            //     break;
            // }
        }
        case 2: {
            // Body completed and here we are
            // Pop context
        }
    }

    if (!ret) {
        // We're done. 
        // Remove from the tasklist (?)

    }

    return ret;
}

// Top-level action is a bit different, since the
// function is blocking
void pss_top_Entry(pss_top_t *ctxt) {
    uint32_t    i;
    pss_top_Entry_t entry;

    for (i=0; i<1000; i++) {
        // Producer traversal
        entry.repeat_P = pss_top_Producer_ctor(ctxt);

        entry.repeat_P->base.base.vtable->randomize(&entry.repeat_P->base.base);

        // This is a 'move' operation
        entry.repeat_P_dat_o = entry.repeat_P->dat_o;
        entry.repeat_P->dat_o = 0;

        entry.repeat_C = pss_top_Consumer_ctor(
            ctxt, 
            entry.repeat_P_dat_o); // This is a non-own reference

        // Need to perform scope cleanup
        // Actions local to the scope
        if (entry.repeat_P) {
            entry.repeat_P->base.base.vtable->dtor(0);
        }
        if (entry.repeat_C) {
            entry.repeat_C->base.base.vtable->dtor(0);
        }
        if (entry.repeat_P_dat_o) {
            entry.repeat_P_dat_o->base.vtable->dtor(0);
        }
    }

//leave:
    // Release any buffers from this scope


}

