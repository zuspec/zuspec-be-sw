#include <stdio.h>
#include "hello_world.h"

void print(const char *s) {
    fprintf(stdout, "PRINT: %s\n", s);
}

int main() {
    pss_top_Entry_actor_t   actor;
    int ret;

    pss_top_Entry_actor_init(&actor);

    actor.funcs.print_f = &print;

    while ((ret=zsp_rt_run_one_task(&actor.actor))) {
        ;
    }
}

