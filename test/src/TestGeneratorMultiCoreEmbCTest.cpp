/*
 * TestGeneratorMultiCoreEmbCTest.cpp
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
#include "GeneratorMultiCoreEmbCTest.h"
#include "NameMap.h"
#include "zsp/arl/dm/impl/ModelBuildContext.h"
#include "vsc/dm/IDataTypeInt.h"
#include "TestGeneratorMultiCoreEmbCTest.h"
#include "TaskGenerateActionQueueCalls.h"

using namespace vsc::dm;
using namespace zsp::arl::dm;

namespace zsp {
namespace be {
namespace sw {


TestGeneratorMultiCoreEmbCTest::TestGeneratorMultiCoreEmbCTest() {

}

TestGeneratorMultiCoreEmbCTest::~TestGeneratorMultiCoreEmbCTest() {

}

TEST_F(TestGeneratorMultiCoreEmbCTest, smoke) {
    NameMap name_m;
    IModelActivityScopeUP activities(m_ctxt->mkModelActivityScope(ModelActivityScopeT::Sequence));
    std::vector<IModelFieldActionUP>   actions;

    m_ctxt->getDebugMgr()->enable(true);
    
    IDataTypeIntUP uint32(m_ctxt->mkDataTypeInt(false, 32));

    vsc::dm::IDataTypeStruct *claim_t = m_ctxt->mkDataTypeStruct("claim_t");
    m_ctxt->addDataTypeStruct(claim_t);

    IDataTypeComponent *comp_t = m_ctxt->mkDataTypeComponent("comp_t");
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec1", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec2", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec3", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec4", claim_t, false));
    m_ctxt->addDataTypeComponent(comp_t);


    // Use a data type in order to get a claim
    IDataTypeAction *action_t = m_ctxt->mkDataTypeAction("action_t");
    action_t->addField(m_ctxt->mkTypeFieldExecutorClaim("claim", claim_t, false));
    action_t->addField(m_ctxt->mkTypeFieldPhy("val1", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    action_t->addField(m_ctxt->mkTypeFieldPhy("val2", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    action_t->setComponentType(comp_t);

    ITypeProcStmtScope *body = m_ctxt->mkTypeProcStmtScope();
    vsc::dm::IModelValUP val(m_ctxt->mkModelValU(5, 32));
    body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("a", uint32.get(), false, 
        m_ctxt->mkTypeExprVal(val.get())));
    val->set_val_u(10);
    body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("b", uint32.get(), false, 
        m_ctxt->mkTypeExprVal(val.get())));
    body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("c", uint32.get(), false, 0));
    body->addStatement(m_ctxt->mkTypeProcStmtAssign(
        m_ctxt->mkTypeExprFieldRef({ // c
            {TypeExprFieldRefElemKind::BottomUpScope, 0},
            {TypeExprFieldRefElemKind::IdxOffset, 2}
        }),
        TypeProcStmtAssignOp::Eq,
        m_ctxt->mkTypeExprBin(
            m_ctxt->mkTypeExprFieldRef({ // a
                {TypeExprFieldRefElemKind::BottomUpScope, 0},
                {TypeExprFieldRefElemKind::IdxOffset, 0}
            }),
            BinOp::Add,
            m_ctxt->mkTypeExprFieldRef({ // b
                {TypeExprFieldRefElemKind::BottomUpScope, 0},
                {TypeExprFieldRefElemKind::IdxOffset, 1}
            }))
        )
    );
    val->set_val_u(1);
    body->addStatement(m_ctxt->mkTypeProcStmtAssign(
        m_ctxt->mkTypeExprFieldRef({ // val2
            {TypeExprFieldRefElemKind::ActiveScope, 0},
            {TypeExprFieldRefElemKind::IdxOffset, 3}
        }),
        TypeProcStmtAssignOp::Eq,
        m_ctxt->mkTypeExprBin(
            m_ctxt->mkTypeExprFieldRef({ // val1
                {TypeExprFieldRefElemKind::ActiveScope, 0},
                {TypeExprFieldRefElemKind::IdxOffset, 2}
            }),
            BinOp::Add,
            m_ctxt->mkTypeExprVal(val.get())
            )
        )
    );

    action_t->addExec(m_ctxt->mkTypeExecProc(ExecKindT::Body, body));
    m_ctxt->addDataTypeAction(action_t);

    // TODO: add an exec body

    arl::dm::ModelBuildContext build_ctxt(m_ctxt.get());
    IModelFieldComponentRootUP comp(comp_t->mkRootFieldT<IModelFieldComponentRoot>(
        &build_ctxt,
        "pss_top",
        false));
    comp->initCompTree();
    IModelFieldExecutor *exec1 = comp->getFieldT<IModelFieldExecutor>(0);
    IModelFieldExecutor *exec2 = comp->getFieldT<IModelFieldExecutor>(1);
    IModelFieldExecutor *exec3 = comp->getFieldT<IModelFieldExecutor>(2);
    IModelFieldExecutor *exec4 = comp->getFieldT<IModelFieldExecutor>(3);

    for (uint32_t i=0; i<16; i++) {
        IModelFieldAction *action = action_t->mkRootFieldT<IModelFieldAction>(
            &build_ctxt, "a", false);
        IModelFieldExecutorClaim *claim = action->getFieldT<IModelFieldExecutorClaim>(1);
        IModelField *val1 = action->getField(2);
        val1->val()->set_val_u(i);
        claim->setRef((i%2)?exec2:exec1);
        actions.push_back(IModelFieldActionUP(action));
        IModelActivityTraverse *t = m_ctxt->mkModelActivityTraverse(
            action,
            0, // with_c
            false, // own_with_c
            0, // activity
            false // own_activiy
            );
        activities->addActivity(t, true);
    }

    IOutputUP out_c;
    IOutputUP out_h;

    ASSERT_TRUE((out_c = IOutputUP(openOutput("test.c"))));
    ASSERT_TRUE((out_h = IOutputUP(openOutput("test.h"))));

    out_c->println("#include <stdio.h>");
    out_c->println("#include \"test.h\"");

    std::vector<IModelFieldExecutor *> executors({exec1, exec2, exec3, exec4});
    IModelEvalIterator *activity_it = m_ctxt->mkModelEvalIterator(activities.get());

    GeneratorMultiCoreEmbCTest(
        m_ctxt->getDebugMgr(),
        executors,
        0,
        out_h.get(),
        out_c.get()).generate(comp.get(), activity_it);

    out_c->println("int main() {");
    out_c->inc_ind();
    out_c->println("fprintf(stdout, \"PASSED\\n\");");
    out_c->dec_ind();
    out_c->println("}");

    out_c->close();
    out_h->close();

    compileAndRun({
        "test.c",
    });
}

TEST_F(TestGeneratorMultiCoreEmbCTest, multi_comp_context) {
    NameMap name_m;
    IModelActivityScopeUP activities(m_ctxt->mkModelActivityScope(ModelActivityScopeT::Sequence));
    std::vector<IModelFieldActionUP>   actions;

    m_ctxt->getDebugMgr()->enable(true);
    
    IDataTypeIntUP uint32(m_ctxt->mkDataTypeInt(false, 32));

    vsc::dm::IDataTypeStruct *claim_t = m_ctxt->mkDataTypeStruct("claim_t");
    m_ctxt->addDataTypeStruct(claim_t);

    IDataTypeComponent *sub_comp_t = m_ctxt->mkDataTypeComponent("sub_comp_t");
    m_ctxt->addDataTypeComponent(sub_comp_t);

    IDataTypeComponent *comp_t = m_ctxt->mkDataTypeComponent("comp_t");
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec1", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec2", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec3", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec4", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldPhy("c1", sub_comp_t, false, TypeFieldAttr::NoAttr, 0));
    comp_t->addField(m_ctxt->mkTypeFieldPhy("c2", sub_comp_t, false, TypeFieldAttr::NoAttr, 0));
    comp_t->addField(m_ctxt->mkTypeFieldPhy("c3", sub_comp_t, false, TypeFieldAttr::NoAttr, 0));
    comp_t->addField(m_ctxt->mkTypeFieldPhy("c4", sub_comp_t, false, TypeFieldAttr::NoAttr, 0));
    m_ctxt->addDataTypeComponent(comp_t);


    // Use a data type in order to get a claim
    IDataTypeAction *action_t = m_ctxt->mkDataTypeAction("action_t");
    action_t->addField(m_ctxt->mkTypeFieldExecutorClaim("claim", claim_t, false));
    action_t->addField(m_ctxt->mkTypeFieldPhy("val1", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    action_t->addField(m_ctxt->mkTypeFieldPhy("val2", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    action_t->setComponentType(sub_comp_t);

    ITypeProcStmtScope *body = m_ctxt->mkTypeProcStmtScope();
    vsc::dm::IModelValUP val(m_ctxt->mkModelValU(5, 32));
    body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("a", uint32.get(), false, 
        m_ctxt->mkTypeExprVal(val.get())));
    val->set_val_u(10);
    body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("b", uint32.get(), false, 
        m_ctxt->mkTypeExprVal(val.get())));
    body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("c", uint32.get(), false, 0));
    body->addStatement(m_ctxt->mkTypeProcStmtAssign(
        m_ctxt->mkTypeExprFieldRef({ // c
            {TypeExprFieldRefElemKind::BottomUpScope, 0},
            {TypeExprFieldRefElemKind::IdxOffset, 2}
        }),
        TypeProcStmtAssignOp::Eq,
        m_ctxt->mkTypeExprBin(
            m_ctxt->mkTypeExprFieldRef({ // a
                {TypeExprFieldRefElemKind::BottomUpScope, 0},
                {TypeExprFieldRefElemKind::IdxOffset, 0}
            }),
            BinOp::Add,
            m_ctxt->mkTypeExprFieldRef({ // b
                {TypeExprFieldRefElemKind::BottomUpScope, 0},
                {TypeExprFieldRefElemKind::IdxOffset, 1}
            }))
        )
    );
    val->set_val_u(1);
    body->addStatement(m_ctxt->mkTypeProcStmtAssign(
        m_ctxt->mkTypeExprFieldRef({ // val2
            {TypeExprFieldRefElemKind::ActiveScope, 0},
            {TypeExprFieldRefElemKind::IdxOffset, 3}
        }),
        TypeProcStmtAssignOp::Eq,
        m_ctxt->mkTypeExprBin(
            m_ctxt->mkTypeExprFieldRef({ // val1
                {TypeExprFieldRefElemKind::ActiveScope, 0},
                {TypeExprFieldRefElemKind::IdxOffset, 2}
            }),
            BinOp::Add,
            m_ctxt->mkTypeExprVal(val.get())
            )
        )
    );

    action_t->addExec(m_ctxt->mkTypeExecProc(ExecKindT::Body, body));
    m_ctxt->addDataTypeAction(action_t);

    // TODO: add an exec body

    arl::dm::ModelBuildContext build_ctxt(m_ctxt.get());
    IModelFieldComponentRootUP comp(comp_t->mkRootFieldT<IModelFieldComponentRoot>(
        &build_ctxt,
        "pss_top",
        false));
    comp->initCompTree();
    IModelFieldExecutor *exec1 = comp->getFieldT<IModelFieldExecutor>(1);
    IModelFieldExecutor *exec2 = comp->getFieldT<IModelFieldExecutor>(2);
    IModelFieldExecutor *exec3 = comp->getFieldT<IModelFieldExecutor>(3);
    IModelFieldExecutor *exec4 = comp->getFieldT<IModelFieldExecutor>(4);
    IModelFieldComponent *c1 = comp->getFieldT<IModelFieldComponent>(5);
    IModelFieldComponent *c2 = comp->getFieldT<IModelFieldComponent>(6);
    IModelFieldComponent *c3 = comp->getFieldT<IModelFieldComponent>(7);
    IModelFieldComponent *c4 = comp->getFieldT<IModelFieldComponent>(8);

    ASSERT_TRUE(exec1);
    ASSERT_TRUE(exec2);
    ASSERT_TRUE(exec3);
    ASSERT_TRUE(exec4);
    ASSERT_TRUE(c1);
    ASSERT_TRUE(c2);
    ASSERT_TRUE(c3);
    ASSERT_TRUE(c4);

    for (uint32_t i=0; i<16; i++) {
        IModelFieldAction *action = action_t->mkRootFieldT<IModelFieldAction>(
            &build_ctxt, "a", false);
        IModelFieldRef *comp = action->getFieldT<IModelFieldRef>(0);
        IModelFieldExecutorClaim *claim = action->getFieldT<IModelFieldExecutorClaim>(1);
        IModelField *val1 = action->getField(2);
        val1->val()->set_val_u(i);
        claim->setRef((i%2)?exec2:exec1);
        switch (i%4) {
            case 0: comp->setRef(c1); break;
            case 1: comp->setRef(c2); break;
            case 2: comp->setRef(c3); break;
            case 3: comp->setRef(c4); break;
        }

        actions.push_back(IModelFieldActionUP(action));
        IModelActivityTraverse *t = m_ctxt->mkModelActivityTraverse(
            action,
            0, // with_c
            false, // own_with_c
            0, // activity
            false // own_activiy
            );
        activities->addActivity(t, true);
    }

    IOutputUP out_c;
    IOutputUP out_h;

    ASSERT_TRUE((out_c = IOutputUP(openOutput("test.c"))));
    ASSERT_TRUE((out_h = IOutputUP(openOutput("test.h"))));

    out_c->println("#include <stdio.h>");
    out_c->println("#include \"test.h\"");

    std::vector<IModelFieldExecutor *> executors({exec1, exec2, exec3, exec4});
    IModelEvalIterator *activity_it = m_ctxt->mkModelEvalIterator(activities.get());

    GeneratorMultiCoreEmbCTest(
        m_ctxt->getDebugMgr(),
        executors,
        0,
        out_h.get(),
        out_c.get()).generate(comp.get(), activity_it);

    out_c->println("int main() {");
    out_c->inc_ind();
    out_c->println("fprintf(stdout, \"PASSED\\n\");");
    out_c->dec_ind();
    out_c->println("}");

    out_c->close();
    out_h->close();

    compileAndRun({
        "test.c",
    });
}

TEST_F(TestGeneratorMultiCoreEmbCTest, import_func_call) {
    NameMap name_m;
    IModelActivityScopeUP activities(m_ctxt->mkModelActivityScope(ModelActivityScopeT::Sequence));
    std::vector<IModelFieldActionUP>   actions;

    m_ctxt->getDebugMgr()->enable(true);
    
    IDataTypeIntUP uint32(m_ctxt->mkDataTypeInt(false, 32));

    vsc::dm::IDataTypeStruct *claim_t = m_ctxt->mkDataTypeStruct("claim_t");
    m_ctxt->addDataTypeStruct(claim_t);

    IDataTypeFunctionUP doit(m_ctxt->mkDataTypeFunction("doit", 0, false));
    doit->addImportSpec(m_ctxt->mkDataTypeFunctionImport("C"));

    IDataTypeComponent *sub_comp_t = m_ctxt->mkDataTypeComponent("sub_comp_t");
    m_ctxt->addDataTypeComponent(sub_comp_t);

    IDataTypeComponent *comp_t = m_ctxt->mkDataTypeComponent("comp_t");
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec1", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec2", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldPhy("c1", sub_comp_t, false, TypeFieldAttr::NoAttr, 0));
    comp_t->addField(m_ctxt->mkTypeFieldPhy("c2", sub_comp_t, false, TypeFieldAttr::NoAttr, 0));
    m_ctxt->addDataTypeComponent(comp_t);


    // Use a data type in order to get a claim
    IDataTypeAction *action_t = m_ctxt->mkDataTypeAction("action_t");
    action_t->addField(m_ctxt->mkTypeFieldExecutorClaim("claim", claim_t, false));
    action_t->addField(m_ctxt->mkTypeFieldPhy("val1", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    action_t->addField(m_ctxt->mkTypeFieldPhy("val2", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    action_t->setComponentType(sub_comp_t);

    ITypeProcStmtScope *body = m_ctxt->mkTypeProcStmtScope();
    vsc::dm::IModelValUP val(m_ctxt->mkModelValU(5, 32));
    body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("a", uint32.get(), false, 
        m_ctxt->mkTypeExprVal(val.get())));
    val->set_val_u(10);
    body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("b", uint32.get(), false, 
        m_ctxt->mkTypeExprVal(val.get())));
    body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("c", uint32.get(), false, 0));
    body->addStatement(m_ctxt->mkTypeProcStmtAssign(
        m_ctxt->mkTypeExprFieldRef({ // c
            {TypeExprFieldRefElemKind::BottomUpScope, 0},
            {TypeExprFieldRefElemKind::IdxOffset, 2}
        }),
        TypeProcStmtAssignOp::Eq,
        m_ctxt->mkTypeExprBin(
            m_ctxt->mkTypeExprFieldRef({ // a
                {TypeExprFieldRefElemKind::BottomUpScope, 0},
                {TypeExprFieldRefElemKind::IdxOffset, 0}
            }),
            BinOp::Add,
            m_ctxt->mkTypeExprFieldRef({ // b
                {TypeExprFieldRefElemKind::BottomUpScope, 0},
                {TypeExprFieldRefElemKind::IdxOffset, 1}
            }))
        )
    );
    body->addStatement(m_ctxt->mkTypeProcStmtExpr(
        m_ctxt->mkTypeExprMethodCallStatic(
            doit.get(),
            {}
        )));
    val->set_val_u(1);
    body->addStatement(m_ctxt->mkTypeProcStmtAssign(
        m_ctxt->mkTypeExprFieldRef({ // val2
            {TypeExprFieldRefElemKind::ActiveScope, 0},
            {TypeExprFieldRefElemKind::IdxOffset, 3}
        }),
        TypeProcStmtAssignOp::Eq,
        m_ctxt->mkTypeExprBin(
            m_ctxt->mkTypeExprFieldRef({ // val1
                {TypeExprFieldRefElemKind::ActiveScope, 0},
                {TypeExprFieldRefElemKind::IdxOffset, 2}
            }),
            BinOp::Add,
            m_ctxt->mkTypeExprVal(val.get())
            )
        )
    );

    action_t->addExec(m_ctxt->mkTypeExecProc(ExecKindT::Body, body));
    m_ctxt->addDataTypeAction(action_t);

    // TODO: add an exec body

    arl::dm::ModelBuildContext build_ctxt(m_ctxt.get());
    IModelFieldComponentRootUP comp(comp_t->mkRootFieldT<IModelFieldComponentRoot>(
        &build_ctxt,
        "pss_top",
        false));
    comp->initCompTree();
    IModelFieldExecutor *exec1 = comp->getFieldT<IModelFieldExecutor>(1);
    IModelFieldExecutor *exec2 = comp->getFieldT<IModelFieldExecutor>(2);
    IModelFieldComponent *c1 = comp->getFieldT<IModelFieldComponent>(3);
    IModelFieldComponent *c2 = comp->getFieldT<IModelFieldComponent>(4);

    ASSERT_TRUE(exec1);
    ASSERT_TRUE(exec2);
    ASSERT_TRUE(c1);
    ASSERT_TRUE(c2);

    for (uint32_t i=0; i<2; i++) {
        IModelFieldAction *action = action_t->mkRootFieldT<IModelFieldAction>(
            &build_ctxt, "a", false);
        IModelFieldRef *comp = action->getFieldT<IModelFieldRef>(0);
        IModelFieldExecutorClaim *claim = action->getFieldT<IModelFieldExecutorClaim>(1);
        IModelField *val1 = action->getField(2);
        val1->val()->set_val_u(i);
        claim->setRef((i%2)?exec2:exec1);
        switch (i%2) {
            case 0: comp->setRef(c1); break;
            case 1: comp->setRef(c2); break;
        }

        actions.push_back(IModelFieldActionUP(action));
        IModelActivityTraverse *t = m_ctxt->mkModelActivityTraverse(
            action,
            0, // with_c
            false, // own_with_c
            0, // activity
            false // own_activiy
            );
        activities->addActivity(t, true);
    }

    IOutputUP out_c;
    IOutputUP out_h;

    ASSERT_TRUE((out_c = IOutputUP(openOutput("test.c"))));
    ASSERT_TRUE((out_h = IOutputUP(openOutput("test.h"))));

    out_c->println("#include <stdio.h>");
    out_c->println("#include \"test.h\"");

    std::vector<IModelFieldExecutor *> executors({exec1, exec2});
    IModelEvalIterator *activity_it = m_ctxt->mkModelEvalIterator(activities.get());

    GeneratorMultiCoreEmbCTest(
        m_ctxt->getDebugMgr(),
        executors,
        0,
        out_h.get(),
        out_c.get()).generate(comp.get(), activity_it);
    out_c->println("void doit() {");
    out_c->println("}");

    out_c->println("");
    out_c->println("int main() {");
    out_c->inc_ind();
    out_c->println("fprintf(stdout, \"PASSED\\n\");");
    out_c->dec_ind();
    out_c->println("}");

    out_c->close();
    out_h->close();

    compileAndRun({
        "test.c",
    });
}

TEST_F(TestGeneratorMultiCoreEmbCTest, no_executors) {
    NameMap name_m;
    IModelActivityScopeUP activities(m_ctxt->mkModelActivityScope(ModelActivityScopeT::Sequence));
    std::vector<IModelFieldActionUP>   actions;

    m_ctxt->getDebugMgr()->enable(true);
    
    IDataTypeIntUP uint32(m_ctxt->mkDataTypeInt(false, 32));

    vsc::dm::IDataTypeStruct *claim_t = m_ctxt->mkDataTypeStruct("claim_t");
    m_ctxt->addDataTypeStruct(claim_t);

    IDataTypeFunctionUP doit(m_ctxt->mkDataTypeFunction("doit", 0, false));
    doit->addImportSpec(m_ctxt->mkDataTypeFunctionImport("C"));

    IDataTypeComponent *sub_comp_t = m_ctxt->mkDataTypeComponent("sub_comp_t");
    m_ctxt->addDataTypeComponent(sub_comp_t);

    IDataTypeComponent *comp_t = m_ctxt->mkDataTypeComponent("comp_t");
    comp_t->addField(m_ctxt->mkTypeFieldPhy("c1", sub_comp_t, false, TypeFieldAttr::NoAttr, 0));
    comp_t->addField(m_ctxt->mkTypeFieldPhy("c2", sub_comp_t, false, TypeFieldAttr::NoAttr, 0));
    m_ctxt->addDataTypeComponent(comp_t);


    // Use a data type in order to get a claim
    IDataTypeAction *action_t = m_ctxt->mkDataTypeAction("action_t");
    action_t->addField(m_ctxt->mkTypeFieldPhy("val1", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    action_t->addField(m_ctxt->mkTypeFieldPhy("val2", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    action_t->setComponentType(sub_comp_t);

    ITypeProcStmtScope *body = m_ctxt->mkTypeProcStmtScope();
    vsc::dm::IModelValUP val(m_ctxt->mkModelValU(5, 32));
    body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("a", uint32.get(), false, 
        m_ctxt->mkTypeExprVal(val.get())));
    val->set_val_u(10);
    body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("b", uint32.get(), false, 
        m_ctxt->mkTypeExprVal(val.get())));
    body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("c", uint32.get(), false, 0));
    body->addStatement(m_ctxt->mkTypeProcStmtAssign(
        m_ctxt->mkTypeExprFieldRef({ // c
            {TypeExprFieldRefElemKind::BottomUpScope, 0},
            {TypeExprFieldRefElemKind::IdxOffset, 2}
        }),
        TypeProcStmtAssignOp::Eq,
        m_ctxt->mkTypeExprBin(
            m_ctxt->mkTypeExprFieldRef({ // a
                {TypeExprFieldRefElemKind::BottomUpScope, 0},
                {TypeExprFieldRefElemKind::IdxOffset, 0}
            }),
            BinOp::Add,
            m_ctxt->mkTypeExprFieldRef({ // b
                {TypeExprFieldRefElemKind::BottomUpScope, 0},
                {TypeExprFieldRefElemKind::IdxOffset, 1}
            }))
        )
    );
    body->addStatement(m_ctxt->mkTypeProcStmtExpr(
        m_ctxt->mkTypeExprMethodCallStatic(
            doit.get(),
            {}
        )));
    val->set_val_u(1);
    body->addStatement(m_ctxt->mkTypeProcStmtAssign(
        m_ctxt->mkTypeExprFieldRef({ // val2
            {TypeExprFieldRefElemKind::ActiveScope, 0},
            {TypeExprFieldRefElemKind::IdxOffset, 2}
        }),
        TypeProcStmtAssignOp::Eq,
        m_ctxt->mkTypeExprBin(
            m_ctxt->mkTypeExprFieldRef({ // val1
                {TypeExprFieldRefElemKind::ActiveScope, 0},
                {TypeExprFieldRefElemKind::IdxOffset, 1}
            }),
            BinOp::Add,
            m_ctxt->mkTypeExprVal(val.get())
            )
        )
    );

    action_t->addExec(m_ctxt->mkTypeExecProc(ExecKindT::Body, body));
    m_ctxt->addDataTypeAction(action_t);

    // TODO: add an exec body

    arl::dm::ModelBuildContext build_ctxt(m_ctxt.get());
    IModelFieldComponentRootUP comp(comp_t->mkRootFieldT<IModelFieldComponentRoot>(
        &build_ctxt,
        "pss_top",
        false));
    comp->initCompTree();
    IModelFieldComponent *c1 = comp->getFieldT<IModelFieldComponent>(1);
    IModelFieldComponent *c2 = comp->getFieldT<IModelFieldComponent>(2);

    ASSERT_TRUE(c1);
    ASSERT_TRUE(c2);

    for (uint32_t i=0; i<2; i++) {
        IModelFieldAction *action = action_t->mkRootFieldT<IModelFieldAction>(
            &build_ctxt, "a", false);
        IModelFieldRef *comp = action->getFieldT<IModelFieldRef>(0);
        IModelField *val1 = action->getField(2);
        val1->val()->set_val_u(i);
        switch (i%2) {
            case 0: comp->setRef(c1); break;
            case 1: comp->setRef(c2); break;
        }

        actions.push_back(IModelFieldActionUP(action));
        IModelActivityTraverse *t = m_ctxt->mkModelActivityTraverse(
            action,
            0, // with_c
            false, // own_with_c
            0, // activity
            false // own_activiy
            );
        activities->addActivity(t, true);
    }

    IOutputUP out_c;
    IOutputUP out_h;

    ASSERT_TRUE((out_c = IOutputUP(openOutput("test.c"))));
    ASSERT_TRUE((out_h = IOutputUP(openOutput("test.h"))));

    out_c->println("#include <stdio.h>");
    out_c->println("#include \"test.h\"");

    std::vector<IModelFieldExecutor *> executors({});
    IModelEvalIterator *activity_it = m_ctxt->mkModelEvalIterator(activities.get());

    GeneratorMultiCoreEmbCTest(
        m_ctxt->getDebugMgr(),
        executors,
        0,
        out_h.get(),
        out_c.get()).generate(comp.get(), activity_it);
    out_c->println("void doit() {");
    out_c->println("}");

    out_c->println("");
    out_c->println("int main() {");
    out_c->inc_ind();
    out_c->println("fprintf(stdout, \"PASSED\\n\");");
    out_c->dec_ind();
    out_c->println("}");

    out_c->close();
    out_h->close();

    compileAndRun({
        "test.c",
    });
}

}
}
}
