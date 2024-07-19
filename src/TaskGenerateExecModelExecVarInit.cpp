/*
 * TaskGenerateExecModelExecVarInit.cpp
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
#include "zsp/arl/dm/ITypeProcStmtVarDecl.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelExecVarInit.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelExecVarInit::TaskGenerateExecModelExecVarInit(
    TaskGenerateExecModel       *gen,
    IOutput                     *out) : m_gen(gen), m_out(out) {

}

TaskGenerateExecModelExecVarInit::~TaskGenerateExecModelExecVarInit() {

}

void TaskGenerateExecModelExecVarInit::generate(arl::dm::ITypeProcStmtVarDecl *var) {
    m_var = var;
    var->getDataType()->accept(m_this);
}

void TaskGenerateExecModelExecVarInit::visitDataTypeAddrClaim(arl::dm::IDataTypeAddrClaim *t) {
    /*
    m_out->println("%s = {.store=0, .offset=0};",
        m_var->name().c_str());
     */
}

void TaskGenerateExecModelExecVarInit::visitDataTypeAddrHandle(arl::dm::IDataTypeAddrHandle *t) {
    m_out->println("%s = (zsp_rt_addr_handle_t){.store=0, .offset=0};",
        m_var->name().c_str());
}

void TaskGenerateExecModelExecVarInit::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    m_out->println("%s__init(actor, &%s);",
        m_gen->getNameMap()->getName(t).c_str(),
        m_var->name().c_str());
}

}
}
}
