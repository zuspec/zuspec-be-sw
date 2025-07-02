
#ifndef INCLUDED_ZSP_ACTIVITY_TRAVERSE_H
#define INCLUDED_ZSP_ACTIVITY_TRAVERSE_H
#ifdef __cplusplus
extern "C" {
#endif

struct zsp_frame_s;
struct zsp_thread_s;
struct zsp_action_s;
struct zsp_action_type_s;
struct zsp_activity_ctxt_s;

typedef void (*zsp_activity_traverse_init_f)(
    struct zsp_frame_s         *frame,
    struct zsp_action_s        *action);

struct zsp_frame_s *zsp_activity_traverse(
    struct zsp_thread_s         *thread, 
    struct zsp_activity_ctxt_s  *ctxt,
    struct zsp_action_type_s    *action_t);

struct zsp_frame_s *zsp_activity_traverse_type(
    struct zsp_thread_s         *thread, 
    struct zsp_activity_ctxt_s  *ctxt,
    struct zsp_action_type_s    *action_t,
    zsp_activity_traverse_init_f init);

typedef struct zsp_activity_traverse_s {
} zsp_activity_traverse_t;



#ifdef __cplusplus
}
#endif
#endif /* INCLUDED_ZSP_ACTIVITY_TRAVERSE_H */
