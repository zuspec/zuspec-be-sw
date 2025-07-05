/*
 * TaskGenerateActor.cpp
 *
 * Copyright 2023 Matthew Ballance and Contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may 
 * not use this file except in compliance with the License.  
 * You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software 
 * distributed under the License is distributed on an "AS IS" BASIS, 
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
 * See the License for the specific language governing permissions and 
 * limitations under the License.
 *
 * Created on:
 *     Author:
 */
#include <algorithm>
#include "dmgr/impl/DebugMacros.h"
#include "TaskGenerateActor.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateActor::TaskGenerateActor(
    IContext    *ctxt, 
    IOutput     *out_h,
    IOutput     *out_c) : m_ctxt(ctxt), m_out_h(out_h), m_out_c(out_c) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateActor", ctxt->getDebugMgr());
}

TaskGenerateActor::~TaskGenerateActor() {

}

void TaskGenerateActor::generate(
        arl::dm::IDataTypeComponent *comp_t,
        arl::dm::IDataTypeAction    *action_t) {
    DEBUG_ENTER("generate");

    std::string fullname;
    fullname = m_ctxt->nameMap()->getName(action_t);

    std::string action_name = action_t->name();
    std::replace(action_name.begin(), action_name.end(), ':', '_');

    m_out_h->println("#ifndef INCLUDED_ACTOR_%s", action_name.c_str());
    m_out_h->println("#define INCLUDED_ACTOR_%s", action_name.c_str());
    m_out_h->println("#include \"zsp/be/sw/rt/zsp_actor.h\"");
    m_out_h->println("#include \"model_api.h\"");
    m_out_h->println("#include \"%s.h\"", m_ctxt->nameMap()->getName(comp_t).c_str());

    m_out_h->println("typedef struct %s_actor_s {", action_name.c_str());
    m_out_h->inc_ind();
    m_out_h->println("zsp_actor_base_t base;");
    m_out_h->println("%s_t comp;", m_ctxt->nameMap()->getName(comp_t).c_str());
    m_out_h->println("%s_t exec;", "zsp_executor");
    m_out_h->dec_ind();
    m_out_h->println("} %s_actor_t;", action_name.c_str());
    m_out_h->println("");
    m_out_h->println("zsp_actor_type_t *%s_actor__type();", action_name.c_str());

//    my_actor_init(&actor, a=4, b=7)
    m_out_h->println("#endif /* INCLUDED_ACTOR_%s */", action_name.c_str());

    m_out_c->println("#include \"zsp/be/sw/rt/zsp_activity_ctxt.h\"");
    m_out_c->println("#include \"zsp/be/sw/rt/zsp_activity_traverse.h\"");
    m_out_c->println("#include \"zsp/be/sw/rt/zsp_init_ctxt.h\"");
    m_out_c->println("#include \"%s_actor.h\"", action_name.c_str());
    m_out_c->println("#include \"%s.h\"", m_ctxt->nameMap()->getName(comp_t).c_str());
    m_out_c->println("#include \"%s.h\"", m_ctxt->nameMap()->getName(action_t).c_str());
    m_out_c->println("");

    /**
     * Actor _init function
     */
    m_out_c->println("static void %s_actor_init(zsp_actor_base_t *actor, zsp_api_t *api) {",
        action_name.c_str());
    m_out_c->inc_ind();
    m_out_c->println("%s_actor_t *self = (%s_actor_t *)actor;", action_name.c_str(), action_name.c_str());
    m_out_c->println("zsp_actor_init(");
    m_out_c->inc_ind();
    m_out_c->println("(zsp_actor_t *)actor,");
    m_out_c->println("api,");
    m_out_c->println("(zsp_component_type_t *)%s__type(),", m_ctxt->nameMap()->getName(comp_t).c_str());
    m_out_c->println("(zsp_action_type_t *)%s__type());", m_ctxt->nameMap()->getName(action_t).c_str());
    m_out_c->println("zsp_actor_base(actor)->type = %s_actor__type();", action_name.c_str());
    m_out_c->println("self->exec.api = api;");
    m_out_c->dec_ind();
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("");

    /**
     * Actor _action_init function
     */
    m_out_c->println("static void %s__action_init(zsp_frame_t *frame, zsp_action_t *action) {",
        action_name.c_str());
    m_out_c->inc_ind();
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("");

    /**
     * Actor _run_task function
     */
    m_out_c->println("static zsp_frame_t *%s_run_task(zsp_thread_t *thread, int32_t idx, va_list *args) {",
        action_name.c_str());
    m_out_c->inc_ind();
    m_out_c->println("zsp_frame_t *ret = thread->leaf;");
    m_out_c->println("struct __locals_s {");
    m_out_c->inc_ind();
    m_out_c->println("zsp_activity_ctxt_t ctxt;");
    m_out_c->dec_ind();
    m_out_c->println("};");
    m_out_c->println("");
    m_out_c->println("switch (idx) {");
    m_out_c->inc_ind();
    m_out_c->println("case 0: {");
    m_out_c->inc_ind();
    m_out_c->println("struct __locals_s *__locals;");
    m_out_c->println("zsp_actor_t *actor = va_arg(*args, zsp_actor_t *);");
    m_out_c->println("zsp_alloc_t *alloc = va_arg(*args, zsp_alloc_t *);");
    m_out_c->println("void *action_args = va_arg(*args, void *);");
    m_out_c->println("ret = zsp_thread_alloc_frame(thread, sizeof(struct __locals_s), &%s_run_task);",
        action_name.c_str());
    m_out_c->println("__locals = zsp_frame_locals(ret, struct __locals_s);");
    m_out_c->println("zsp_activity_ctxt_init_root(&__locals->ctxt, alloc, &actor->comp);");
    m_out_c->println("ret->idx = 1;");
    m_out_c->println("ret = zsp_activity_traverse_type(");
    m_out_c->inc_ind();
    m_out_c->println("thread,");
    m_out_c->println("&__locals->ctxt,");
    m_out_c->println("(zsp_action_type_t *)%s__type(),", m_ctxt->nameMap()->getName(action_t).c_str());
    m_out_c->println("%s__action_init);", action_name.c_str());
    m_out_c->dec_ind();

    m_out_c->println("if (ret) break;");
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("default: {");
    m_out_c->inc_ind();
    m_out_c->println("ret = zsp_thread_return(thread, 0);");
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("return ret;");
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("");

    /**
     * Actor _run function
     */
    m_out_c->println("static zsp_thread_t *%s_actor_run(zsp_actor_base_t *actor_b, zsp_scheduler_t *sched, void *args) {",
        action_name.c_str());
    m_out_c->inc_ind();
    m_out_c->println("%s_actor_t *actor = (%s_actor_t *)actor_b;",
        action_name.c_str(), action_name.c_str());
    m_out_c->println("zsp_init_ctxt_t ctxt = {.alloc=sched->alloc, .api=actor->base.api};");
    m_out_c->println("// First, initialize the component tree");
    m_out_c->println("((zsp_component_type_t *)%s__type())->init(&ctxt, zsp_component(&actor->comp), \"pss_top\", 0);", 
        action_name.c_str());
    m_out_c->println("zsp_component_type(&actor->comp)->do_init((zsp_executor_t *)&actor->exec, (zsp_struct_t *)&actor->comp);");
    m_out_c->println("");
    m_out_c->println("return zsp_thread_init(");
    m_out_c->inc_ind();
    m_out_c->println("sched,");
    m_out_c->println("&actor->base.thread,");
    m_out_c->println("&%s_run_task,", action_name.c_str());
    m_out_c->println("ZSP_THREAD_FLAGS_NONE,");
    m_out_c->println("actor,");
    m_out_c->println("sched->alloc,");
    m_out_c->println("args);");
    m_out_c->dec_ind();
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("");

    /**
     * Actor _dtor function
     */
    m_out_c->println("static void %s_actor_dtor(zsp_actor_base_t *actor) {", action_name.c_str());
    m_out_c->inc_ind();
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("");

    /**
     * Actor _type function
     */
    m_out_c->println("zsp_actor_type_t *%s_actor__type() {", action_name.c_str());
    m_out_c->inc_ind();
    m_out_c->println("static zsp_actor_type_t actor_t = {");
    m_out_c->inc_ind();
    m_out_c->println(".name = \"%s\",", action_name.c_str());
    m_out_c->println(".size = sizeof(%s_actor_t),", action_name.c_str());
    m_out_c->println(".init = &%s_actor_init,", action_name.c_str());
    m_out_c->println(".run = &%s_actor_run,", action_name.c_str());
    m_out_c->println(".dtor = &%s_actor_dtor,", action_name.c_str());
    m_out_c->dec_ind();
    m_out_c->println("};");
    m_out_c->println("");
    m_out_c->println("return &actor_t;");
    m_out_c->dec_ind();
    m_out_c->println("}");
    

    DEBUG_LEAVE("generate");
}

dmgr::IDebug *TaskGenerateActor::m_dbg = 0;

}
}
}
