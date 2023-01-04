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
#include "vsc/dm/ITypeExprVal.h"
#include "TaskGenerateEmbCExpr.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateEmbCExpr::TaskGenerateEmbCExpr(NameMap *name_m) : 
    m_name_m(name_m), m_out(0) {
    m_type_scope = 0;
    m_proc_scopes = 0;
}

TaskGenerateEmbCExpr::~TaskGenerateEmbCExpr() {

}

void TaskGenerateEmbCExpr::generate(
        IOutput                                         *out,
        vsc::dm::ITypeField                             *type_scope,
        std::vector<arl::dm::ITypeProcStmtDeclScope *>  *proc_scopes,
        vsc::dm::ITypeExpr                              *expr) {
    m_out = out;
    m_type_scope = type_scope;
    m_proc_scopes = proc_scopes;
    expr->accept(m_this);
}

void TaskGenerateEmbCExpr::visitTypeExprBin(vsc::dm::ITypeExprBin *e) {
    std::map<vsc::dm::BinOp, std::string> op_m = {
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
	    {vsc::dm::BinOp::Xor, "^"},
	    {vsc::dm::BinOp::Not, "!"}
    };

    e->lhs()->accept(m_this);
    m_out->write(" %s ", op_m.find(e->op())->second.c_str());
    e->rhs()->accept(m_this);
}

void TaskGenerateEmbCExpr::visitTypeExprFieldRef(vsc::dm::ITypeExprFieldRef *e) {
    // Walk through the elements of the expression
    if (e->getPath().at(0).kind == vsc::dm::TypeExprFieldRefElemKind::BottomUpScope) {
        // We start by identifying the proc scope
        arl::dm::ITypeProcStmtDeclScope *s = m_proc_scopes->at(
            m_proc_scopes->size() - e->getPath().at(0).idx - 1
        );

        // Next element must be an offset
        arl::dm::ITypeProcStmtVarDecl *v = s->getVariables().at(
            e->getPath().at(1).idx
        );

        m_out->write("%s", v->name().c_str());
        vsc::dm::IDataTypeStruct *dt = dynamic_cast<vsc::dm::IDataTypeStruct *>(v->getDataType());

        for (uint32_t i=2; i<e->getPath().size(); i++) {
            vsc::dm::ITypeField *field = dt->getField(e->getPath().at(i).idx);
            m_out->write(".%s", field->name().c_str());
        }
    } else if (e->getPath().at(0).kind == vsc::dm::TypeExprFieldRefElemKind::ActiveScope) {
        // We start with the type scope
    }
}

void TaskGenerateEmbCExpr::visitTypeExprRange(vsc::dm::ITypeExprRange *e) {

}

void TaskGenerateEmbCExpr::visitTypeExprRangelist(vsc::dm::ITypeExprRangelist *e) {

}

void TaskGenerateEmbCExpr::visitTypeExprVal(vsc::dm::ITypeExprVal *e) {
    // TODO: Should know whether we want a signed or unsigned value
    m_out->write("%lld", e->val()->val_i());
}

}
}
}
