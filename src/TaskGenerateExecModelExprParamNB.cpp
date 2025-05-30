/*
 * TaskGenerateExecModelExprParamNB.cpp
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
#include "vsc/dm/impl/TaskIsTypeFieldRef.h"
#include "vsc/dm/impl/TaskIsExprFieldRef.h"
#include "vsc/dm/impl/TaskIsTypeExprFieldRef.h"
#include "vsc/dm/impl/TaskResolveFieldRefExpr.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelExprParamNB.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelExprParamNB::TaskGenerateExecModelExprParamNB(
    IContext                    *ctxt,
    IGenRefExpr                 *refgen,
    IOutput                     *out) : TaskGenerateExprNB(ctxt, refgen, out) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelExprParamNB", ctxt->getDebugMgr());
}

TaskGenerateExecModelExprParamNB::~TaskGenerateExecModelExprParamNB() {

}

void TaskGenerateExecModelExprParamNB::visitTypeExprRefBottomUp(
    vsc::dm::ITypeExprRefBottomUp *e) {
    DEBUG_ENTER("visitTypeExprRefBottomUp (depth=%d)", m_depth);
    if (!m_depth && m_refgen->isFieldRefExpr(e) && !m_refgen->isRefFieldRefExpr(e)) {
        m_out->write("&");
    }
    TaskGenerateExprNB::visitTypeExprRefBottomUp(e);
    DEBUG_LEAVE("visitTypeExprRefBottomUp (depth=%d)", m_depth);
}

void TaskGenerateExecModelExprParamNB::visitTypeExprRefTopDown(
    vsc::dm::ITypeExprRefTopDown *e) {
    DEBUG_ENTER("visitTypeExprRefTopDown (depth=%d)", m_depth);
    if (!m_depth && m_refgen->isFieldRefExpr(e) && !m_refgen->isRefFieldRefExpr(e)) {
        m_out->write("&");
    }
    TaskGenerateExprNB::visitTypeExprRefTopDown(e);
    DEBUG_LEAVE("visitTypeExprRefTopDown (depth=%d)", m_depth);
}

void TaskGenerateExecModelExprParamNB::visitTypeExprSubField(vsc::dm::ITypeExprSubField *e) {
    DEBUG_ENTER("visitTypeExprSubField");
    if (!m_depth && m_refgen->isFieldRefExpr(e) && !m_refgen->isRefFieldRefExpr(e)) {
        m_out->write("&");
    }
    TaskGenerateExprNB::visitTypeExprSubField(e);
    DEBUG_LEAVE("visitTypeExprSubField");
}

}
}
}
