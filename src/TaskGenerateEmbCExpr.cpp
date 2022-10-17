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
#include "vsc/ITypeExprVal.h"
#include "TaskGenerateEmbCExpr.h"


namespace arl {
namespace be {
namespace sw {


TaskGenerateEmbCExpr::TaskGenerateEmbCExpr(NameMap *name_m) : 
    m_name_m(name_m), m_out(0) {
    m_type_scope = 0;
    m_proc_scope = 0;
}

TaskGenerateEmbCExpr::~TaskGenerateEmbCExpr() {

}

void TaskGenerateEmbCExpr::generate(
        IOutput             *out,
        vsc::ITypeField     *type_scope,
        ITypeProcStmtScope  *proc_scope,
        vsc::ITypeExpr      *expr) {
    m_out = out;
    m_type_scope = type_scope;
    m_proc_scope = proc_scope;
    expr->accept(m_this);
}

void TaskGenerateEmbCExpr::visitTypeExprBin(vsc::ITypeExprBin *e) {
    std::map<vsc::BinOp, std::string> op_m = {
    	{vsc::BinOp::Eq, "=="},
	    {vsc::BinOp::Ne, "!="},
    	{vsc::BinOp::Gt, ">"},
	    {vsc::BinOp::Ge, ">="},
	    {vsc::BinOp::Lt, "<"},
	    {vsc::BinOp::Le, "<="},
	    {vsc::BinOp::Add, "+"},
    	{vsc::BinOp::Sub, "-"},
    	{vsc::BinOp::Div, "/"},
	    {vsc::BinOp::Mul, "*"},
	    {vsc::BinOp::Mod, "%"},
	    {vsc::BinOp::BinAnd, "&"},
	    {vsc::BinOp::BinOr, "|" },
    	{vsc::BinOp::LogAnd, "&&"},
	    {vsc::BinOp::LogOr, "|"},
	    {vsc::BinOp::Sll, "<<"},
	    {vsc::BinOp::Srl, ">>"},
	    {vsc::BinOp::Xor, "^"},
	    {vsc::BinOp::Not, "!"}
    };

    e->lhs()->accept(m_this);
    m_out->write(" %s ", op_m.find(e->op())->second.c_str());
    e->rhs()->accept(m_this);
}

void TaskGenerateEmbCExpr::visitTypeExprFieldRef(vsc::ITypeExprFieldRef *e) {
    // Walk through the elements of the expression

    ITypeProcStmtScope *s = m_proc_scope;
    uint32_t start = 0;

    // Really want to be able to:
    // - Reference a parameter
    // - Reference a variable upward-relative to our current procedural scope
    // - Reference a type variable as an absolute type name (a::b::c)

    // TODO: just the simple case for now
    ITypeProcStmtVarDecl *var_decl = dynamic_cast<ITypeProcStmtVarDecl *>(
        m_proc_scope->getStatements().at(e->getPath().at(0).idx).get());
    m_out->write("%s", var_decl->name().c_str());

}

void TaskGenerateEmbCExpr::visitTypeExprRange(vsc::ITypeExprRange *e) {

}

void TaskGenerateEmbCExpr::visitTypeExprRangelist(vsc::ITypeExprRangelist *e) {

}

void TaskGenerateEmbCExpr::visitTypeExprVal(vsc::ITypeExprVal *e) {
    // TODO: Should know whether we want a signed or unsigned value
    m_out->write("%lld", e->val()->val_i());
}

}
}
}
