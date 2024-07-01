/*
 * TaskGenerateExecModelCustomGenBase.cpp
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
#include "TaskGenerateExecModelFwdDecl.h"
#include "TaskGenerateExecModelCustomGenBase.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelCustomGenBase::TaskGenerateExecModelCustomGenBase(
    dmgr::IDebugMgr         *dmgr) : m_dbg(0) {

}

TaskGenerateExecModelCustomGenBase::~TaskGenerateExecModelCustomGenBase() {

}

void TaskGenerateExecModelCustomGenBase::genExprMethodCallStaticB(
        TaskGenerateExecModel               *gen,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallStatic  *call) { }

void TaskGenerateExecModelCustomGenBase::genExprMethodCallStaticNB(
        TaskGenerateExecModel               *gen,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallStatic  *call) { }

void TaskGenerateExecModelCustomGenBase::genExprMethodCallContextB(
        TaskGenerateExecModel               *gen,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallContext *call) { }

void TaskGenerateExecModelCustomGenBase::genExprMethodCallContextNB(
        TaskGenerateExecModel               *gen,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallContext *call) { }
        
void TaskGenerateExecModelCustomGenBase::genFwdDecl(
        TaskGenerateExecModel               *gen,
        IOutput                             *out,
        vsc::dm::IDataType                  *type) {
    TaskGenerateExecModelFwdDecl(gen, out).generate_dflt(type);
}

void TaskGenerateExecModelCustomGenBase::genDefinition(
        TaskGenerateExecModel               *gen,
        IOutput                             *out_h,
        IOutput                             *out_c,
        vsc::dm::IDataType                  *type) {

}

}
}
}
