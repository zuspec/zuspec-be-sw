/*
 * TaskGenerateExecModelMkExecBodyFuncs.cpp
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
#include "TaskGenerateExecModelMkExecBodyFuncs.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelMkExecBodyFuncs::TaskGenerateExecModelMkExecBodyFuncs(
    TaskGenerateExecModel *gen) : m_gen(gen) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelMkExecBodyFuncs", gen->getDebugMgr());
}

TaskGenerateExecModelMkExecBodyFuncs::~TaskGenerateExecModelMkExecBodyFuncs() {

}

std::vector<arl::dm::IDataTypeFunction *> TaskGenerateExecModelMkExecBodyFuncs::generate(
    const std::vector<vsc::dm::IDataType *> types) {
    DEBUG_ENTER("generate");
    m_funcs.clear();
    for (std::vector<vsc::dm::IDataType *>::const_iterator
        it=types.begin();
        it!=types.end(); it++) {
        (*it)->accept(m_this);
    }
    DEBUG_LEAVE("generate");
    return m_funcs;
}

void TaskGenerateExecModelMkExecBodyFuncs::visitDataTypeAction(arl::dm::IDataTypeAction *i) {
    DEBUG_ENTER("visitDataTypeAction");
    const std::vector<arl::dm::ITypeExecUP> &execs = 
        i->getExecs(arl::dm::ExecKindT::Body);
    if (execs.size()) {
        arl::dm::IContext *ctxt = m_gen->getContext();
        arl::dm::IDataTypeFunction *func = ctxt->mkDataTypeFunction(
            i->name() + "::body",
            0, false,
            arl::dm::DataTypeFunctionFlags::Target);

        if (execs.size() == 1) {
        } else {
            for (std::vector<arl::dm::ITypeExecUP>::const_iterator
                it=execs.begin();
                it!=execs.end(); it++) {
            
            
            }
        }
    }
    DEBUG_LEAVE("visitDataTypeAction");
}

dmgr::IDebug *TaskGenerateExecModelMkExecBodyFuncs::m_dbg = 0;

}
}
}
