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
#include "ITaskGenerateExecModelCustomGen.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelExprNB.h"
#include "TaskGenerateExecModelExprParamNB.h"
#include "TaskGenerateExecModelExprVal.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelExprNB::TaskGenerateExecModelExprNB(
        TaskGenerateExecModel       *gen,
        IGenRefExpr                 *refgen,
        IOutput                     *out) : m_dbg(0),
        m_gen(gen), m_refgen(refgen), m_out(out), m_depth(0) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelExprNB", gen->getDebugMgr());
}

TaskGenerateExecModelExprNB::~TaskGenerateExecModelExprNB() {

}

void TaskGenerateExecModelExprNB::generate(vsc::dm::ITypeExpr *e) {
    DEBUG_ENTER("generate");
    m_depth = 0;
    e->accept(m_this);
    DEBUG_LEAVE("generate");
}

void TaskGenerateExecModelExprNB::visitTypeExprArrIndex(vsc::dm::ITypeExprArrIndex *e) { 

}

static const char *op_m[] = {
	"==", // Eq,
	"!=", // Ne,
	">",  // Gt,
	">=", // Ge,
	"<",  // Lt,
	"<=", // Le,
	"+",  // Add,
	"-",  // Sub,
	"/",  // Div,
	"*",  // Mul,
	"%",  // Mod,
	"&",  // BinAnd,
	"|",  // BinOr,
	"^",  // BinXor,
	"&&", // LogAnd,
	"||", // LogOr,
	"^^", // LogXor,
	"<<", // Sll,
	">>", // Srl,
	"!",  // Not
};

void TaskGenerateExecModelExprNB::visitTypeExprBin(vsc::dm::ITypeExprBin *e) {
    m_depth++;
    e->lhs()->accept(m_this);

    m_out->write(" %s ", op_m[(int)e->op()]);

    e->rhs()->accept(m_this);
    m_depth--;
}

void TaskGenerateExecModelExprNB::visitTypeExprFieldRef(vsc::dm::ITypeExprFieldRef *e) { 

}

void TaskGenerateExecModelExprNB::visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) { 
    DEBUG_ENTER("VisitTypeExprMethodCallContext %s",
        e->getTarget()->name().c_str());
    m_depth++;
    ITaskGenerateExecModelCustomGen *custom_gen = 
        dynamic_cast<ITaskGenerateExecModelCustomGen *>(e->getTarget()->getAssociatedData());

    DEBUG("custom_gen: %p (%p)", custom_gen, e->getTarget()->getAssociatedData());
    if (custom_gen) {
        custom_gen->genExprMethodCallContextNB(
            m_gen,
            m_out,
            m_refgen,
            e);
    } else {
        m_out->write("%s(", 
            m_gen->getNameMap()->getName(e->getTarget()).c_str()
        );
        for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
            it=e->getParameters().begin();
            it!=e->getParameters().end(); it++) {
            if (it != e->getParameters().begin()) {
                m_out->write(", ");
            }
            TaskGenerateExecModelExprParamNB(m_gen, m_refgen, m_out).generate(
                it->get()
            );
        }
        m_out->write(")");
    }
    m_depth--;
    DEBUG_LEAVE("VisitTypeExprMethodCallContext");
}

void TaskGenerateExecModelExprNB::visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) { 
    DEBUG_ENTER("VisitTypeExprMethodCallStatic");
    m_depth++;
    ITaskGenerateExecModelCustomGen *custom_gen = 
        dynamic_cast<ITaskGenerateExecModelCustomGen *>(e->getTarget()->getAssociatedData());

    if (custom_gen) {
        custom_gen->genExprMethodCallStaticNB(
            m_gen,
            m_out,
            m_refgen,
            e);
    } else {
        m_out->write("%s(", 
            m_gen->getNameMap()->getName(e->getTarget()).c_str()
        );
        for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
            it=e->getParameters().begin();
            it!=e->getParameters().end(); it++) {
            if (it != e->getParameters().begin()) {
                m_out->write(", ");
            }
            TaskGenerateExecModelExprParamNB(m_gen, m_refgen, m_out).generate(it->get());
        }
        m_out->write(")");
    }
    m_depth--;
    DEBUG_LEAVE("VisitTypeExprMethodCallStatic");
}

void TaskGenerateExecModelExprNB::visitTypeExprRange(vsc::dm::ITypeExprRange *e) { 

}

void TaskGenerateExecModelExprNB::visitTypeExprRangelist(vsc::dm::ITypeExprRangelist *e) { 

}

void TaskGenerateExecModelExprNB::visitTypeExprRefBottomUp(vsc::dm::ITypeExprRefBottomUp *e) {
    DEBUG_ENTER("visitTypeExprRefBottomUp");
    m_depth++;
    m_out->write("%s", m_refgen->genRval(e).c_str());
    m_depth--;
    DEBUG_LEAVE("visitTypeExprRefBottomUp");
}

void TaskGenerateExecModelExprNB::visitTypeExprRefPath(vsc::dm::ITypeExprRefPath *e) { 

}

void TaskGenerateExecModelExprNB::visitTypeExprRefTopDown(vsc::dm::ITypeExprRefTopDown *e) { 
    DEBUG_ENTER("visitTypeExprRefTopDown");
    m_depth++;
    m_out->write("%s", m_refgen->genRval(e).c_str());
    m_depth--;
    DEBUG_LEAVE("visitTypeExprRefTopDown");
}

void TaskGenerateExecModelExprNB::visitTypeExprSubField(vsc::dm::ITypeExprSubField *e) { 
    DEBUG_ENTER("visitTypeExprSubField");
    m_depth++;
    m_out->write("%s", m_refgen->genRval(e).c_str());
    m_depth--;
    DEBUG_LEAVE("visitTypeExprSubField");
}

void TaskGenerateExecModelExprNB::visitTypeExprUnary(vsc::dm::ITypeExprUnary *e) { 

}

void TaskGenerateExecModelExprNB::visitTypeExprVal(vsc::dm::ITypeExprVal *e) {
    DEBUG_ENTER("visitTypeExprVal");
    m_depth++;
    TaskGenerateExecModelExprVal(m_gen, m_out).generate(e);
    m_depth--;
    DEBUG_LEAVE("visitTypeExprVal");
}


}
}
}
