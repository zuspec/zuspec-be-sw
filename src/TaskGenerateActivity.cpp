/*
 * TaskGenerateActivity.cpp
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
#include "TaskGenerateExecModel.h"
#include "TaskGenerateActivity.h"
#include "TaskGenerateLocalsActivity.h"
#include "TaskBuildAsyncScopeGroup.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateActivity::TaskGenerateActivity(
    IContext            *ctxt,
    IGenRefExpr         *refgen,
    IOutput             *out,
    const std::string   &fname) : TaskGenerateAsyncBase(ctxt, refgen, out, fname) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateActivity", ctxt->getDebugMgr());
}

TaskGenerateActivity::~TaskGenerateActivity() {

}

void TaskGenerateActivity::generate(vsc::dm::IDataType *activity) {
    DEBUG_ENTER("generate");
    TaskGenerateAsyncBase::generate(activity);
    DEBUG_LEAVE("generate");
}

void TaskGenerateActivity::visitDataTypeActivityTraverseType(arl::dm::IDataTypeActivityTraverseType *t) {
    DEBUG_ENTER("visitDataTypeActivityTraverseType");
    m_out->write("ret->idx = %d;\n", m_next_scope_id);
    m_out->println("ret = zsp_activity_traverse_type(thread, __locals->__ctxt, %s__type(), 0);",
        m_ctxt->nameMap()->getName(t->getTarget()).c_str());
    DEBUG_LEAVE("visitDataTypeActivityTraverseType");
}

void TaskGenerateActivity::generate_locals(vsc::dm::IDataTypeStruct *locals_t) {
    TaskGenerateLocalsActivity(m_ctxt, m_out).generate(locals_t);
}

void TaskGenerateActivity::generate_init_locals() {
    m_out->println("__locals->__ctxt = va_arg(*args, zsp_activity_ctxt_t *);");
}


}
}
}
