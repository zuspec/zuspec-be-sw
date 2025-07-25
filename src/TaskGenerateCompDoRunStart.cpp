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
#include "GenRefExprExecModel.h"
#include "TaskGenerateActivity.h"
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
        char tmp[128];
        std::string fname = m_ctxt->nameMap()->getName(t);
        snprintf(tmp, sizeof(tmp), "_activity_%p", comp_t->activities().at(0).get());
        fname += tmp;
        GenRefExprExecModel refgen(m_ctxt->getDebugMgr(), t, "this_p", true);
        TaskGenerateActivity(m_ctxt, &refgen, m_out_c, fname).generate(
            comp_t->activities().at(0)->getDataType());
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
    m_out_c->println("} *__locals = zsp_frame_locals(ret, struct __locals_s);");
    m_out_c->println("");
    m_out_c->println("switch (idx) {");
    m_out_c->inc_ind();
    m_out_c->println("case 0: {");
    m_out_c->inc_ind();
    m_out_c->println("ret = zsp_thread_alloc_frame(thread, sizeof(struct __locals_s), &%s__do_run_start);",
        m_ctxt->nameMap()->getName(t).c_str());
    m_out_c->println("__locals = zsp_frame_locals(ret, struct __locals_s);");
    m_out_c->println("__locals->self = va_arg(*args, %s_t *);",
        m_ctxt->nameMap()->getName(t).c_str());
    m_out_c->dec_ind();
    m_out_c->println("}");

    // Step 0..N: Evaluate each sub-component 
    // Evaluate bottom-up
    m_idx++;
    for (auto it=t->getFields().begin();
            it!=t->getFields().end(); it++) {
        (*it)->accept(this);
    }

    // Step N+1: Launch local activity (if present)
    // If we have local activities, start those now
    if (comp_t->activities().size() > 0) {
        m_out_c->println("case %d: {", m_idx++);
        m_out_c->inc_ind();
        m_out_c->println("zsp_activity_ctxt_init_root(&__locals->self->activity_%p_ctxt, "
            "thread->sched->alloc, (zsp_component_t *)__locals->self);",
            comp_t->activities().at(0).get());
        m_out_c->println("zsp_thread_init(thread->sched, &__locals->self->activity_%p_thread, "
                "%s_activity_%p, ZSP_THREAD_FLAGS_NONE, &__locals->self->activity_%p_ctxt);",
            comp_t->activities().at(0).get(),
            m_ctxt->nameMap()->getName(t).c_str(),
            comp_t->activities().at(0).get(),
            comp_t->activities().at(0).get());
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
