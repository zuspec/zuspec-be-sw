#include <stdio.h>
#include "hello_world.h"

void print(const char *s) {
    fprintf(stdout, "PRINT: %s\n", s);
}

int main() {
    pss_top_Entry_actor_t   actor;

    pss_top_Entry_actor_init(&actor);

    while (pss_top_Entry_actor_runOneTask(&actor)) {
        ;
    }
}

