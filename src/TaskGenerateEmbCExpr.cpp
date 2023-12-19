/*
 * TaskGenerateEmbCExpr.cpp
 *
 * Copyright 2022 Matthew Ballance and Contributors
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
#include <map>
#include "dmgr/impl/DebugMacros.h"
#include "vsc/dm/ITypeExprVal.h"
#include "vsc/dm/impl/TaskIsTypeFieldRef.h"
#include "zsp/be/sw/IMethodCallFactoryAssocData.h"
#include "TaskGenerateEmbCExpr.h"
#include "TaskGenerateEmbCVal.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateEmbCExpr::TaskGenerateEmbCExpr(IContext *ctxt) :
        m_ctxt(ctxt), m_out(0),
        m_active_ptref(false), m_bottom_up_ptref(false) { 
    DEBUG_INIT("zsp::be::sw::TaskGenerateEmbCExpr", ctxt->getDebugMgr());
}

TaskGenerateEmbCExpr::~TaskGenerateEmbCExpr() {

}

void TaskGenerateEmbCExpr::generate(
        IOutput                                         *out,
        vsc::dm::ITypeExpr                              *expr) {
    DEBUG_ENTER("generate");
    m_out = out;
    expr->accept(m_this);
    DEBUG_LEAVE("generate");
}

static std::map<vsc::dm::BinOp, std::string> prv_op_m = {
    	{vsc::dm::BinOp::Eq, "=="},
	    {vsc::dm::BinOp::Ne, "!="},
    	{vsc::dm::BinOp::Gt, ">"},
	    {vsc::dm::BinOp::Ge, ">="},
	    {vsc::dm::BinOp::Lt, "<"},
	    {vsc::dm::BinOp::Le, "<="},
	    {vsc::dm::BinOp::Add, "+"},
    	{vsc::dm::BinOp::Sub, "-"},
    	{vsc::dm::BinOp::Div, "/"},
	    {vsc::dm::BinOp::Mul, "*"},
	    {vsc::dm::BinOp::Mod, "%"},
	    {vsc::dm::BinOp::BinAnd, "&"},
	    {vsc::dm::BinOp::BinOr, "|" },
    	{vsc::dm::BinOp::LogAnd, "&&"},
	    {vsc::dm::BinOp::LogOr, "|"},
	    {vsc::dm::BinOp::Sll, "<<"},
	    {vsc::dm::BinOp::Srl, ">>"},
	    {vsc::dm::BinOp::BinXor, "^"},
	    {vsc::dm::BinOp::Not, "!"}
};


void TaskGenerateEmbCExpr::visitTypeExprBin(vsc::dm::ITypeExprBin *e) {
    e->lhs()->accept(m_this);
    m_out->write(" %s ", prv_op_m.find(e->op())->second.c_str());
    e->rhs()->accept(m_this);
}

void TaskGenerateEmbCExpr::visitTypeExprFieldRef(vsc::dm::ITypeExprFieldRef *e) {
    // Walk through the elements of the expression
    if (e->getRootRefKind() == vsc::dm::ITypeExprFieldRef::RootRefKind::BottomUpScope) {
        if (m_bottom_up_pref.size()) {
            m_out->write("%s%s", m_bottom_up_pref.c_str(), m_bottom_up_ptref?"->":".");
        }
        // We start by identifying the proc scope
        arl::dm::ITypeProcStmtDeclScope *s = m_ctxt->execScope(e->getRootRefOffset());

        // Next element must be an offset
        arl::dm::ITypeProcStmtVarDecl *v = s->getVariables().at(e->at(0)).get();

        m_out->write("%s", v->name().c_str());
        vsc::dm::IDataTypeStruct *dt = dynamic_cast<vsc::dm::IDataTypeStruct *>(v->getDataType());

        for (uint32_t i=1; i<e->getPath().size(); i++) {
            vsc::dm::ITypeField *field = dt->getField(e->at(i));
            m_out->write(".%s", field->name().c_str());
        }
    } else if (e->getRootRefKind() == vsc::dm::ITypeExprFieldRef::RootRefKind::TopDownScope) {
        // We start with the type scope
        bool prev_ptr = false;
        if (m_active_pref.size()) {
//            prev_ptr = m_active_ptref;
            m_out->write("%s%s", m_active_pref.c_str(), m_active_ptref?"->":".");
        }

        vsc::dm::IDataTypeStruct *scope = m_ctxt->typeScope();
        for (uint32_t i=0; i<e->size(); i++) {
            vsc::dm::ITypeField *field = scope->getField(e->at(i));
            if (i > 1) {
                m_out->write("%s", (prev_ptr)?"->":".");
            }
            m_out->write("%s", field->name().c_str());
            prev_ptr = vsc::dm::TaskIsTypeFieldRef().eval(field);
            scope = field->getDataTypeT<vsc::dm::IDataTypeStruct>();
        }
    }
}

void TaskGenerateEmbCExpr::visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) {
    DEBUG_ENTER("visitTypeExprMethodCallContext");
    fprintf(stdout, "assoc_data: %p", e->getTarget()->getAssociatedData());
    fflush(stdout);
    IMethodCallFactoryAssocData *assoc_data = 
        dynamic_cast<IMethodCallFactoryAssocData *>(e->getTarget()->getAssociatedData());
    if (assoc_data) {
        vsc::dm::ITypeExprUP expr(assoc_data->mkCallContext(m_ctxt, e));
        if (expr) {
            DEBUG_ENTER("Visit expr");
            expr->accept(m_this);
            DEBUG_LEAVE("Visit expr");
        } else {
            DEBUG("Null expr");
        }

        m_out->write(")");
    } else {
        // Directly render the function call
        m_out->println("%s(", m_ctxt->nameMap()->getName(e->getTarget()).c_str());
        m_out->inc_ind();
        for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
            it=e->getParameters().begin();
            it!=e->getParameters().end(); it++) {
            m_out->write(m_out->ind());
            (*it)->accept(m_this);
            if (it+1 != e->getParameters().end()) {
                m_out->write(",\n");
            }
        }
        m_out->dec_ind();
        m_out->write(")\n");
    }
    DEBUG_LEAVE("visitTypeExprMethodCallContext");
}

void TaskGenerateEmbCExpr::visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) {
    DEBUG_ENTER("visitTypeExprMethodCallStatic");
    fprintf(stdout, "assoc_data: %p", e->getTarget()->getAssociatedData());
    fflush(stdout);
    IMethodCallFactoryAssocData *assoc_data = 
        dynamic_cast<IMethodCallFactoryAssocData *>(e->getTarget()->getAssociatedData());
    if (assoc_data) {
        vsc::dm::ITypeExprUP expr(assoc_data->mkCallStatic(m_ctxt, e));
        if (expr) {
            DEBUG_ENTER("Visit expr");
            expr->accept(m_this);
            DEBUG_LEAVE("Visit expr");
        } else {
            DEBUG("Null expr");
        }

        m_out->write(")");
    } else {
        // Directly render the function call
        m_out->println("%s(", m_ctxt->nameMap()->getName(e->getTarget()).c_str());
        m_out->inc_ind();
        for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
            it=e->getParameters().begin();
            it!=e->getParameters().end(); it++) {
            m_out->write(m_out->ind());
            (*it)->accept(m_this);
            if (it+1 != e->getParameters().end()) {
                m_out->write(",\n");
            }
        }
        m_out->dec_ind();
        m_out->write(")\n");
    }
    DEBUG_LEAVE("visitTypeExprMethodCallStatic");
}

void TaskGenerateEmbCExpr::visitTypeExprRange(vsc::dm::ITypeExprRange *e) {

}

void TaskGenerateEmbCExpr::visitTypeExprRangelist(vsc::dm::ITypeExprRangelist *e) {

}

void TaskGenerateEmbCExpr::visitTypeExprVal(vsc::dm::ITypeExprVal *e) {
    DEBUG_ENTER("visitTypeExprVal");
    TaskGenerateEmbCVal(m_ctxt).generate(m_out, e->val());
    DEBUG_LEAVE("visitTypeExprVal");
}

dmgr::IDebug *TaskGenerateEmbCExpr::m_dbg = 0;

}
}
}
