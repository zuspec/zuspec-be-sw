
#ifndef INCLUDED_ZSP_ACTOR_BASE_H
#define INCLUDED_ZSP_ACTOR_BASE_H

typedef struct zsp_actor_base_s {
    // Base class for all actors, providing common functionality
    // and properties that all actors will inherit.
    // This can include methods for initialization, destruction,
    // and other common actor behaviors.

    // Example member variables (to be defined as needed):
    // int actor_id;          // Unique identifier for the actor
    // const char *name;      // Name of the actor
    zsp_bool_t              is_elab;
} zsp_actor_base_t;

#endif /* INCLUDED_ZSP_ACTOR_BASE_H */
