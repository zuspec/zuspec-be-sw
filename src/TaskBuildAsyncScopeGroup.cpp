/*
 * TaskBuildAsyncScopeGroup.cpp
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
#include <set>
#include "dmgr/impl/DebugMacros.h"
#include "TaskBuildAsyncScopeGroup.h"
#include "ScopeLocalsAssociatedData.h"
#include "TypeProcStmtGotoAsyncScope.h"


namespace zsp {
namespace be {
namespace sw {


TaskBuildAsyncScopeGroup::TaskBuildAsyncScopeGroup(IContext *ctxt) : 
    m_ctxt(ctxt), m_locals_root(0), m_scope_changed(false) {
    DEBUG_INIT("zsp.be.sw.TaskBuildAsyncScopeGroup", ctxt->getDebugMgr());
}

TaskBuildAsyncScopeGroup::~TaskBuildAsyncScopeGroup() {

}

TypeProcStmtAsyncScopeGroup *TaskBuildAsyncScopeGroup::build(vsc::dm::IAccept *scope) {
    DEBUG_ENTER("build");    

    m_scopes.push_back(TypeProcStmtAsyncScopeUP(new TypeProcStmtAsyncScope(0)));

    // Default case
    m_scopes.push_back(TypeProcStmtAsyncScopeUP(new TypeProcStmtAsyncScope(-1)));

    scope->accept(m_this);

    if (m_scopes.size() > 2) {
        // An actual async scope was created

        if (m_scopes.at(m_scopes.size()-2)->getStatements().size() == 0) {
            // Remove the last actual scope since it has no statements
            m_scopes.erase(m_scopes.end()-2);
        }
    }

    DEBUG("%d local scopes are identified", m_locals_type_l.size());

    if (m_locals_root) {
        build_scope_types(m_locals_root);
    }

    TypeProcStmtAsyncScopeGroup *ret = new TypeProcStmtAsyncScopeGroup();
    for (std::vector<TypeProcStmtAsyncScopeUP>::iterator
        it=m_scopes.begin();
        it!=m_scopes.end(); it++) {
        ret->addStatement(it->release(), it->owned());
    }
    for (std::vector<vsc::dm::IDataTypeStructUP>::iterator
        it=m_locals_type_l.begin();
        it!=m_locals_type_l.end(); it++) {
        ret->addLocalsType(it->release());
    }

    DEBUG_LEAVE("build %d", m_scopes.size());
    return ret;
}

void TaskBuildAsyncScopeGroup::visitDataTypeAction(arl::dm::IDataTypeAction *t) {
    DEBUG_ENTER("visitDataTypeAction");
    if (t->activities().size() > 0) {
        if (t->activities().size() > 1) {
            // TODO: Create a schedule 
            DEBUG("Action %s has %d activities", t->name().c_str(), t->activities().size());
        } else {
            DEBUG("Action %s has 1 activity", t->name().c_str());
        }
    } else {
        DEBUG("No activities in action %s", t->name().c_str());
    }
    DEBUG_LEAVE("visitDataTypeAction");
}

void TaskBuildAsyncScopeGroup::visitDataTypeActivity(arl::dm::IDataTypeActivity *t) {
    DEBUG_ENTER("visitDataTypeActivity");
    DEBUG_LEAVE("visitDataTypeActivity");
}

void TaskBuildAsyncScopeGroup::visitDataTypeFunction(arl::dm::IDataTypeFunction *t) {
    DEBUG_ENTER("visitDataTypeFunction");
    Locals *locals = new Locals(t->getParamScope(), m_locals_s.size()?m_locals_s.back():0);

    // Already know we need a type
    if (t->getParamScope()->getNumVariables()) {
        locals->type = mk_type();
    }

    if (!m_locals_root) {
        m_locals_root = locals;
    }
    m_locals_s.push_back(locals);

    DEBUG_LEAVE("visitDataTypeFunction");
}

void TaskBuildAsyncScopeGroup::visitTypeExprBin(vsc::dm::ITypeExprBin *e) {
    vsc::dm::ITypeExprUP lhs, rhs;
    m_expr.reset();
    e->lhs()->accept(this);
    lhs = std::move(m_expr);
    m_expr.reset();
    e->rhs()->accept(this);
    rhs = std::move(m_expr);

    if (lhs || rhs) {
        m_expr = vsc::dm::ITypeExprUP(m_ctxt->ctxt()->mkTypeExprBin(
            (lhs)?lhs.get():e->lhs(),
            e->op(),
            (rhs)?rhs.get():e->rhs(),
            lhs.get(),
            rhs.get()
        ));
        lhs.release();
        rhs.release();
    }
}

void TaskBuildAsyncScopeGroup::visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) {
    DEBUG_ENTER("visitTypeExprMethodCallContext");
    TypeProcStmtAsyncScope *scope = currentScope();
    std::vector<vsc::dm::ITypeExprUP> blocking_params;

    // First, visit all parameter expressions 
    for (std::vector<vsc::dm::ITypeExprUP>::const_iterator 
        it=e->getParameters().begin();
        it!=e->getParameters().end(); it++) {
        m_expr.reset();
        (*it)->accept(m_this);
        blocking_params.push_back(std::move(m_expr));
    }

    if (currentScope() != scope) {
        DEBUG("New scope created while evaluating parameters");
        // We need to rewrite the method call, since some of the
        // parameter expressions were blocking

        // TODO: Release any temp variables
    }

    // TODO: if the method itself is blocking, then we need to
    // introduce a new scope with a temp assignment on the other
    // side to retrieve the method result

    DEBUG_LEAVE("visitTypeExprMethodCallContext");
}

void TaskBuildAsyncScopeGroup::visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) {
    DEBUG_ENTER("visitTypeExprMethodCallStatic");
    // TODO: check if this function should be treated as blocking
    bool blocking = true;

    if (blocking) {
        // Initiate the call
        currentScope()->addStatement(m_ctxt->ctxt()->mkTypeProcStmtExpr(e, false));

        TypeProcStmtAsyncScope *next = newScope();
        // Must signal that the statement above has been broken up
    } else {
        // Add as a non-blocking function
    }

//    if (m_imp_target_blocking && e->getTarget()->hasFlags(arl::dm::DataTypeFunctionFlags::Import)) {

    DEBUG_LEAVE("visitTypeExprMethodCallStatic");
}

void TaskBuildAsyncScopeGroup::visitTypeExecProc(arl::dm::ITypeExecProc *e) {
    e->getBody()->accept(m_this);
}

void TaskBuildAsyncScopeGroup::visitTypeProcStmt(arl::dm::ITypeProcStmt *s) {
    DEBUG_ENTER("visitTypeProcStmt");
    DEBUG_LEAVE("visitTypeProcStmt");
}

void TaskBuildAsyncScopeGroup::visitTypeProcStmtRepeat(arl::dm::ITypeProcStmtRepeat *s) { 
    DEBUG_ENTER("vistTypeProcStmtRepeat");

    // Create a new scope to hold iteration variables

    // Establish a scope to hold the key statements
//    arl::dm::ITypeProcStmtScope *scope = m_ctxt->ctxt()->mkTypeProcStmtScope();
//    m_vscopes.push_back(arl::dm::ITypeProcStmtScopeUP(scope));

    // Entering the scope that declares and initializes the iteration variable
    // New-scope ensures that the variable declaration is applied
    enter_scope(s);

    // TODO: Add an initialization statement

    // Establish a new async scope that serves as the head of the loop
    TypeProcStmtAsyncScope *head = newScope();

    // Create an end-of-loop scope
    TypeProcStmtAsyncScope *tail = new TypeProcStmtAsyncScope(-1);

    // TODO: Add a conditional jump to tail scope
    arl::dm::ITypeProcStmtIfClause *i_c = m_ctxt->ctxt()->mkTypeProcStmtIfClause(
        m_ctxt->ctxt()->mkTypeExprBin(
            m_ctxt->ctxt()->mkTypeExprRefBottomUp(0, 0),
            vsc::dm::BinOp::Eq,
            m_ctxt->ctxt()->mkTypeExprRefBottomUp(0, 0)
        ),
        new TypeProcStmtGotoAsyncScope(tail)
    );
    std::vector<arl::dm::ITypeProcStmtIfClause *> if_clauses;
    if_clauses.push_back(i_c);
    arl::dm::ITypeProcStmtIfElse *if_then = m_ctxt->ctxt()->mkTypeProcStmtIfElse(
        if_clauses,
        0
    );
    head->addStatement(if_then, true);

    // Process the body -- potentially adding new async scopes
    s->getBody()->accept(m_this);

    // Finish up by inserting the tail node
    // It will go just before the terminal node
    tail->setId(m_scopes.size()-1);
    m_scopes.insert(m_scopes.end()-1, TypeProcStmtAsyncScopeUP(tail));

    leave_scope();


    DEBUG_LEAVE("vistTypeProcStmtRepeat");
}

void TaskBuildAsyncScopeGroup::visitTypeProcStmtRepeatWhile(arl::dm::ITypeProcStmtRepeatWhile *s) { 

}

void TaskBuildAsyncScopeGroup::visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *s) {
    DEBUG_ENTER("visitTypeProcStmtScope");
    enter_scope(s);
	for (std::vector<arl::dm::ITypeProcStmtUP>::const_iterator
		it=s->getStatements().begin();
		it!=s->getStatements().end(); it++) {
		(*it)->accept(m_this);
	}
    leave_scope();
    DEBUG_LEAVE("visitTypeProcStmtScope");
}

void TaskBuildAsyncScopeGroup::visitTypeProcStmtWhile(arl::dm::ITypeProcStmtWhile *s) { 

}

void TaskBuildAsyncScopeGroup::visitTypeProcStmtYield(arl::dm::ITypeProcStmtYield *s) { 
    DEBUG_ENTER("visitTypeProcStmtYield");
    // This statement belongs in the current scope
    // Need to introduce a new scope for subsequent statements
    m_scopes.at(m_scopes.size()-2)->addStatement(s, false);

    newScope();
    
    DEBUG_LEAVE("visitTypeProcStmtYield");
}

TypeProcStmtAsyncScope *TaskBuildAsyncScopeGroup::newScope() {
    TypeProcStmtAsyncScope *cur = currentScope();
    TypeProcStmtAsyncScope *ret = new TypeProcStmtAsyncScope(cur->id() + 1, m_scope_s);
    m_scopes.insert(m_scopes.end()-1, TypeProcStmtAsyncScopeUP(ret));
    return ret;
}

void TaskBuildAsyncScopeGroup::enter_scope(vsc::dm::ITypeVarScope *s) {
    Locals *locals = new Locals(s, m_locals_s.size()?m_locals_s.back():0);
    m_scope_s.push_back(s);
    m_scope_changed = true;

    if (m_scopes.front()->scopes().size() == 0) {
        m_scopes.front()->pushScope(s);
        m_scopes.back()->pushScope(s);
    }

    // Already know we need a type
    if (s->getNumVariables()) {
        locals->type = mk_type();
    } else {
        if (locals->upper) {
            locals->type = locals->upper->type;
        } else {
            locals->type = mk_type();
        }
    }

    if (!m_locals_root) {
        m_locals_root = locals;
    }
    m_locals_s.push_back(locals);
}

void TaskBuildAsyncScopeGroup::leave_scope() {
    vsc::dm::IDataTypeStruct *type = 0;
    Locals *l = m_locals_s.back();

    if (l->type) {
        // Since we have a unique type, link ourselves into the tree
        if (l->upper) {
            l->upper->children.push_back(l);
        }
        type = l->type;
    } else {
        // Since we don't have a unique type, 
        for (std::vector<Locals *>::const_reverse_iterator
            it=m_locals_s.rbegin();
            it!=m_locals_s.rend(); it++) {
            if ((*it)->type) {
                type = (*it)->type;
                break;
            }
        }
    }

    l->scope->setAssociatedData(new ScopeLocalsAssociatedData(type));

    m_locals_s.pop_back();
    m_scope_s.pop_back();
    m_scope_changed = true;
}

vsc::dm::IDataTypeStruct *TaskBuildAsyncScopeGroup::mk_type() {
    char tmp[64];

    snprintf(tmp, sizeof(tmp), "__locals%d", m_locals_type_l.size());
    vsc::dm::IDataTypeStruct *ret = m_ctxt->ctxt()->mkDataTypeStruct(tmp);
    m_locals_type_l.push_back(vsc::dm::IDataTypeStructUP(ret));

    return ret;
}

void TaskBuildAsyncScopeGroup::build_scope_types(Locals *l) {
    DEBUG_ENTER("build_scope_types %s %d", (l->type)?l->type->name().c_str():"<null>", l->children.size());
    if (l->children.size()) {
        for (std::vector<Locals *>::iterator
            it=l->children.begin();
            it!=l->children.end(); it++) {
            build_scope_types(*it);
        }
    }

    // Now worry about this type
    std::set<std::string> local_names;
    int32_t shadow_id=0;
    // for (std::vector<vsc::dm::ITypeVarUP>::const_iterator
    //     it=l->scope->getVariables().begin();
    //     it!=l->scope->getVariables().end(); it++) {
    //     local_names.insert((*it)->name());
    // }

    add_fields(l->type, l, local_names, shadow_id);
    DEBUG_LEAVE("build_scope_types");
}

vsc::dm::ITypeVar *TaskBuildAsyncScopeGroup::mk_temp(vsc::dm::IDataType *type, bool owned) {
    char tmp[256];

    Locals *locals = m_locals_s.back();

    if (!locals->type) {
        locals->type = mk_type();
    }

    snprintf(tmp, sizeof(tmp), "__tmp%d", m_locals_s.back()->tmpid++);
    arl::dm::ITypeProcStmtVarDecl *tmpvar = m_ctxt->ctxt()->mkTypeProcStmtVarDecl(
        tmp,
        type,
        owned,
        0);
    m_locals_s.back()->scope->addVariable(tmpvar);

    return tmpvar;
}

void TaskBuildAsyncScopeGroup::add_fields(
        vsc::dm::IDataTypeStruct    *type, 
        Locals                      *l,
        std::set<std::string>       &names,
        int32_t                     &shadow_id) {
    DEBUG_ENTER("add_fields %s", type->name().c_str());
    // Add fields depth-first

    // Create the fields that we will add, observing
    // shadowing rules
    std::vector<vsc::dm::ITypeField *> fields;
    for (std::vector<vsc::dm::ITypeVarUP>::const_iterator
        it=l->scope->getVariables().begin();
        it!=l->scope->getVariables().end(); it++) {
        std::string name = (*it)->name();
        DEBUG("name: %s", name.c_str());
        if (names.find(name) != names.end()) {
            char tmp[64];
            // Create a shadow name
            snprintf(tmp, sizeof(tmp), "__shadow_%d", shadow_id++);
            name = tmp;
        } else {
            names.insert(name);
        }
        fields.push_back(m_ctxt->ctxt()->mkTypeFieldPhy(
            name, 
            (*it)->getDataType(),
            false,
            vsc::dm::TypeFieldAttr::NoAttr,
            0));
    }

    if (l->upper) {
        add_fields(type, l->upper, names, shadow_id);
    }

    // Finally, add our fields to the type
    for (std::vector<vsc::dm::ITypeField *>::const_iterator
        it=fields.begin();
        it!=fields.end(); it++) {
        type->addField(*it);
    }

    DEBUG_LEAVE("add_fields %s", type->name().c_str());
}

dmgr::IDebug *TaskBuildAsyncScopeGroup::m_dbg = 0;

}
}
}
