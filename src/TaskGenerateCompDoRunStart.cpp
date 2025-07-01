/*
 * TaskGenerateCompDoRunStart.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "TaskGenerateCompDoRunStart.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateCompDoRunStart::TaskGenerateCompDoRunStart(
        IContext                *ctxt,
        TypeInfo                *info,
        IOutput                 *out_h,
        IOutput                 *out_c) : 
        m_ctxt(ctxt), m_info(info), m_out_h(out_h), m_out_c(out_c) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateCompDoRunStart", m_ctxt->getDebugMgr());
}

TaskGenerateCompDoRunStart::~TaskGenerateCompDoRunStart() {

}

void TaskGenerateCompDoRunStart::generate(vsc::dm::IDataTypeStruct *t) {
    arl::dm::IDataTypeComponent *comp_t = dynamic_cast<arl::dm::IDataTypeComponent *>(t);

    m_idx = 0;

    m_out_h->println("struct zsp_frame_s *%s__do_run_start(struct zsp_thread_s *thread, int32_t idx, va_list *args);",
        m_ctxt->nameMap()->getName(t).c_str(),
        m_ctxt->nameMap()->getName(t).c_str());

    if (comp_t->activities().size() > 0) {
        m_out_c->println("static zsp_frame_t *%s__activity(zsp_thread_t *thread, zsp_frame_t *frame, va_list *args) {",
            m_ctxt->nameMap()->getName(t).c_str());
        m_out_c->inc_ind();
        m_out_c->println("zsp_frame_t *ret = 0;");
        m_out_c->println("int initial = (frame == 0);");
        m_out_c->println("struct __locals_s {");
        m_out_c->inc_ind();
        m_out_c->println("%s_t *self;", m_ctxt->nameMap()->getName(t).c_str());
        m_out_c->println("zsp_executor_t *executor;");
        m_out_c->dec_ind();
        m_out_c->println("} *__locals;");
        m_out_c->println("");
        m_out_c->println("if (!frame) {");
        m_out_c->inc_ind();
        m_out_c->println("frame = zsp_thread_alloc_frame(thread, sizeof(struct __locals_s), &%s__activity);",
            m_ctxt->nameMap()->getName(t).c_str());
        m_out_c->dec_ind();
        m_out_c->println("}");
        m_out_c->println("__locals = (struct __locals_s *)&((zsp_frame_wrap_t *)frame)->locals;");
        m_out_c->println("ret = frame;");

        m_out_c->println("if (initial) {");
        m_out_c->inc_ind();
        m_out_c->println("__locals->self = va_arg(*args, %s_t *);",
            m_ctxt->nameMap()->getName(t).c_str());
        m_out_c->dec_ind();
        m_out_c->println("}");

        m_out_c->println("return ret;");
        m_out_c->dec_ind();
        m_out_c->println("}");
    }

    m_out_c->println("zsp_frame_t *%s__do_run_start(zsp_thread_t *thread, int32_t idx, va_list *args) {",
        m_ctxt->nameMap()->getName(t).c_str(),
        m_ctxt->nameMap()->getName(t).c_str());
    m_out_c->inc_ind();

    // Preliminaries
    m_out_c->println("zsp_frame_t *ret = thread->leaf;");
    m_out_c->println("struct __locals_s {");
    m_out_c->inc_ind();
    m_out_c->println("%s_t *self;", m_ctxt->nameMap()->getName(t).c_str());
    m_out_c->println("zsp_executor_t *executor;");
    m_out_c->dec_ind();
    m_out_c->println("} *__locals;");
    // m_out_c->println("if (!frame) {");
    // m_out_c->inc_ind();
    // m_out_c->println("frame = zsp_thread_alloc_frame(thread, zsp_frame_size(struct __locals_s), &%s__do_run_start);",
    //     m_ctxt->nameMap()->getName(t).c_str());
    // m_out_c->dec_ind();
    // m_out_c->println("}");
    // m_out_c->println("__locals = (struct __locals_s *)&((zsp_frame_wrap_t *)frame)->locals;");
    // m_out_c->println("ret = frame;");


    // m_out_c->println("");
    // m_out_c->println("if (initial) {");
    // m_out_c->inc_ind();
    // m_out_c->println("__locals->self = va_arg(*args, %s_t *);",
    //     m_ctxt->nameMap()->getName(t).c_str());
    // m_out_c->println("__locals->executor = va_arg(*args, zsp_executor_t *);");
    // m_out_c->dec_ind();
    // m_out_c->println("}");

    m_out_c->println("switch (idx) {");
    m_out_c->inc_ind();
    // Step 0..N: Evaluate each sub-component 
    // Evaluate bottom-up
    for (auto it=t->getFields().begin();
            it!=t->getFields().end(); it++) {
        (*it)->accept(this);
    }
    // Step N+1: Launch local activity (if present)
    // If we have local activities, start those now
    if (comp_t->activities().size() > 0) {
        m_out_c->println("case %d: {", m_idx++);
        m_out_c->inc_ind();
        m_out_c->println("zsp_thread_create(thread->sched, &%s__activity, ZSP_THREAD_FLAGS_NONE, __locals->self);",
            m_ctxt->nameMap()->getName(t).c_str());
//        m_out_c->println("zsp_component_type(&frame->self)->do_run_start_activities(thread, frame);");
        m_out_c->dec_ind();
        m_out_c->println("}");
    }

    // Finally, complete
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

}

void TaskGenerateCompDoRunStart::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    if (m_is_ref) {
        // TODO:
    } else {
        m_out_c->println("zsp_component_type(&self->%s)->do_init(actor, (zsp_struct_t *)&self->%s);",
            m_ctxt->nameMap()->getName(m_field).c_str(),
            m_ctxt->nameMap()->getName(m_field).c_str());
    }

}

void TaskGenerateCompDoRunStart::visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) {
    m_field = f;
    m_is_ref = false;
    f->getDataType()->accept(this);
}

void TaskGenerateCompDoRunStart::visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) {
    m_field = f;
    m_is_ref = true;
    f->getDataType()->accept(this);
}

dmgr::IDebug *TaskGenerateCompDoRunStart::m_dbg = 0;

}
}
}
