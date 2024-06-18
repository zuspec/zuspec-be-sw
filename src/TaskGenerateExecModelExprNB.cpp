/*
 * TaskGenerateExecModelExprNB.cpp
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
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelExprNB.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelExprNB::TaskGenerateExecModelExprNB(
        TaskGenerateExecModel       *gen,
        GenRefExprExecModel         *refgen,
        IOutput                     *out) :
        m_gen(gen), m_refgen(refgen), m_out(out) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelExprNB", gen->getDebugMgr());
}

TaskGenerateExecModelExprNB::~TaskGenerateExecModelExprNB() {

}

void TaskGenerateExecModelExprNB::visitTypeExprArrIndex(vsc::dm::ITypeExprArrIndex *e) { }

void TaskGenerateExecModelExprNB::visitTypeExprBin(vsc::dm::ITypeExprBin *e) { }

void TaskGenerateExecModelExprNB::visitTypeExprFieldRef(vsc::dm::ITypeExprFieldRef *e) { }

void TaskGenerateExecModelExprNB::visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) { }

void TaskGenerateExecModelExprNB::visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) { }

void TaskGenerateExecModelExprNB::visitTypeExprRange(vsc::dm::ITypeExprRange *e) { }

void TaskGenerateExecModelExprNB::visitTypeExprRangelist(vsc::dm::ITypeExprRangelist *e) { }

void TaskGenerateExecModelExprNB::visitTypeExprRefBottomUp(vsc::dm::ITypeExprRefBottomUp *e) { }

void TaskGenerateExecModelExprNB::visitTypeExprRefPath(vsc::dm::ITypeExprRefPath *e) { }

void TaskGenerateExecModelExprNB::visitTypeExprRefTopDown(vsc::dm::ITypeExprRefTopDown *e) { }

void TaskGenerateExecModelExprNB::visitTypeExprSubField(vsc::dm::ITypeExprSubField *e) { }

void TaskGenerateExecModelExprNB::visitTypeExprUnary(vsc::dm::ITypeExprUnary *e) { }

void TaskGenerateExecModelExprNB::visitTypeExprVal(vsc::dm::ITypeExprVal *e) {

}

dmgr::IDebug *TaskGenerateExecModelExprNB::m_dbg = 0;

}
}
}
