
#ifndef INCLUDED_ZSP_ACTIVITY_TRAVERSE_H
#define INCLUDED_ZSP_ACTIVITY_TRAVERSE_H
#ifdef __cplusplus
extern "C" {
#endif

struct zsp_frame_s;
struct zsp_thread_s;
struct zsp_action_type_s;

struct zsp_frame_s *zsp_activity_traverse(
    struct zsp_thread_s         *thread, 
    struct zsp_frame_s          *frame,
    struct zsp_action_type_s    *action_t);

typedef struct zsp_activity_traverse_s {
} zsp_activity_traverse_t;


#ifdef __cplusplus
}
#endif
#endif /* INCLUDED_ZSP_ACTIVITY_TRAVERSE_H */
