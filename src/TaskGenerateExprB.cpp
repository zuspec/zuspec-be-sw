/*
 * TaskGenerateExprB.cpp
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
#include "TaskGenerateExprB.h"
#include "ITaskGenerateExecModelCustomGen.h"
#include "TaskGenerateExecModelExprParamNB.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExprB::TaskGenerateExprB(
        IContext                    *ctxt,
        IGenRefExpr                 *refgen,
        IOutput                     *out) : TaskGenerateExprNB(ctxt, refgen, out) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateExprB", ctxt->getDebugMgr());
}

TaskGenerateExprB::~TaskGenerateExprB() {

}
void TaskGenerateExprB::visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) { 
    DEBUG_ENTER("VisitTypeExprMethodCallContext %s",
        e->getTarget()->name().c_str());
    m_depth++;
    ITaskGenerateExecModelCustomGen *custom_gen = 
        dynamic_cast<ITaskGenerateExecModelCustomGen *>(e->getTarget()->getAssociatedData());

    DEBUG("custom_gen: %p (%p)", custom_gen, e->getTarget()->getAssociatedData());
    if (custom_gen) {
        custom_gen->genExprMethodCallContextB(
            m_ctxt,
            m_out,
            m_refgen,
            e);
    } else {
        m_out->write("%s(", 
            m_ctxt->nameMap()->getName(e->getTarget()).c_str()
        );
        for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
            it=e->getParameters().begin();
            it!=e->getParameters().end(); it++) {
            if (it != e->getParameters().begin()) {
                m_out->write(", ");
            }
            TaskGenerateExecModelExprParamNB(m_ctxt, m_refgen, m_out).generate(
                it->get()
            );
        }
        m_out->write(")");
    }
    m_depth--;
    DEBUG_LEAVE("VisitTypeExprMethodCallContext");
}

void TaskGenerateExprB::visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) { 
    DEBUG_ENTER("VisitTypeExprMethodCallStatic");
    m_depth++;
    ITaskGenerateExecModelCustomGen *custom_gen = 
        dynamic_cast<ITaskGenerateExecModelCustomGen *>(e->getTarget()->getAssociatedData());

    if (custom_gen) {
        custom_gen->genExprMethodCallStaticB(
            m_ctxt,
            m_out,
            m_refgen,
            e);
    } else {
        m_out->write("%s(", 
            m_ctxt->nameMap()->getName(e->getTarget()).c_str()
        );
        for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
            it=e->getParameters().begin();
            it!=e->getParameters().end(); it++) {
            if (it != e->getParameters().begin()) {
                m_out->write(", ");
            }
            TaskGenerateExecModelExprParamNB(m_ctxt, m_refgen, m_out).generate(it->get());
        }
        m_out->write(")");
    }
    m_depth--;
    DEBUG_LEAVE("VisitTypeExprMethodCallStatic");
}

}
}
}
