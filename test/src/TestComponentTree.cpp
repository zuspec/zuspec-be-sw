/*
 * TestComponentTree.cpp
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
#include "NameMap.h"
#include "TestComponentTree.h"
#include "zsp/arl/dm/impl/ModelBuildContext.h"
#include "vsc/dm/IDataTypeInt.h"
#include "TestGeneratorMultiCoreEmbCTest.h"
#include "TaskGenerateActionQueueCalls.h"

namespace zsp {
namespace be {
namespace sw {

using namespace vsc::dm;
using namespace zsp::arl::dm;

TestComponentTree::TestComponentTree() {

}

TestComponentTree::~TestComponentTree() {

}

TEST_F(TestComponentTree, smoke) {
    fprintf(stdout, "TestComponentTree::smoke\n");
}

TEST_F(TestComponentTree, multi_level_comp) {
    NameMap name_m;
    IModelActivityScopeUP activities(m_ctxt->mkModelActivityScope(ModelActivityScopeT::Sequence));
    std::vector<IModelFieldActionUP>   actions;

    m_ctxt->getDebugMgr()->enable(true);
    
    IDataTypeIntUP uint32(m_ctxt->mkDataTypeInt(false, 32));

    IDataTypeComponent *comp_sub_t = m_ctxt->mkDataTypeComponent("comp_sub_t");
    comp_sub_t->addField(m_ctxt->mkTypeFieldPhy("f1", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    comp_sub_t->addField(m_ctxt->mkTypeFieldPhy("f2", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    m_ctxt->addDataTypeComponent(comp_sub_t);

    IDataTypeComponent *comp_t = m_ctxt->mkDataTypeComponent("comp_t");
    comp_t->addField(m_ctxt->mkTypeFieldPhy("c1", comp_sub_t, false, TypeFieldAttr::NoAttr, 0));
    comp_t->addField(m_ctxt->mkTypeFieldPhy("c2", comp_sub_t, false, TypeFieldAttr::NoAttr, 0));
    comp_t->addField(m_ctxt->mkTypeFieldPhy("c3", comp_sub_t, false, TypeFieldAttr::NoAttr, 0));
    m_ctxt->addDataTypeComponent(comp_t);

    IDataTypeAction *action_t = m_ctxt->mkDataTypeAction("comp_sub_t::action_t");
    action_t->addField(m_ctxt->mkTypeFieldPhy("val1", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    action_t->addField(m_ctxt->mkTypeFieldPhy("val2", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    action_t->setComponentType(comp_t);

    ITypeProcStmtScope *body = m_ctxt->mkTypeProcStmtScope();
    vsc::dm::IModelValUP val(m_ctxt->mkModelValU(5, 32));
    // body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("a", uint32.get(), false, 
    //     m_ctxt->mkTypeExprVal(val.get())));
    // val->set_val_u(10);
    // body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("b", uint32.get(), false, 
    //     m_ctxt->mkTypeExprVal(val.get())));
    body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("c", uint32.get(), false, 0));
    body->addStatement(m_ctxt->mkTypeProcStmtAssign(
        m_ctxt->mkTypeExprFieldRef(
            ITypeExprFieldRef::RootRefKind::BottomUpScope, 0, {2} // c
        ),
        TypeProcStmtAssignOp::Eq,
        m_ctxt->mkTypeExprBin(
            m_ctxt->mkTypeExprFieldRef(
                ITypeExprFieldRef::RootRefKind::BottomUpScope, 0, {0} // a
            ),
            BinOp::Add,
            m_ctxt->mkTypeExprFieldRef(
                ITypeExprFieldRef::RootRefKind::BottomUpScope, 0, {1} // b
            ))
        )
    );
    val->set_val_u(1);
    // body->addStatement(m_ctxt->mkTypeProcStmtAssign(
    //     m_ctxt->mkTypeExprFieldRef(
    //         ITypeExprFieldRef::RootRefKind::TopDownScope, 0, {2} // val2
    //     ),
    //     TypeProcStmtAssignOp::Eq,
    //     m_ctxt->mkTypeExprBin(
    //         m_ctxt->mkTypeExprFieldRef(
    //             ITypeExprFieldRef::RootRefKind::TopDownScope, 0, {1} // val1
    //         ),
    //         BinOp::Add,
    //         m_ctxt->mkTypeExprVal(val.get())
    //         )
    //     )
    // );

    action_t->addExec(m_ctxt->mkTypeExecProc(ExecKindT::Body, body));
    action_t->setComponentType(comp_sub_t);
    comp_sub_t->addActionType(action_t);
    m_ctxt->addDataTypeAction(action_t);

    // TODO: add an exec body

    arl::dm::ModelBuildContext build_ctxt(m_ctxt.get());
    IModelFieldComponentRootUP comp(comp_t->mkRootFieldT<IModelFieldComponentRoot>(
        &build_ctxt,
        "pss_top",
        false));
    comp->initCompTree();

    std::vector<vsc::dm::IModelField *> components;
    for (uint32_t i=1; i<=3; i++) {
        components.push_back(comp->getField(i));
    }

    for (uint32_t i=0; i<16; i++) {
        IModelFieldAction *action = action_t->mkRootFieldT<IModelFieldAction>(
            &build_ctxt, "a", false);
        IModelFieldRef *comp = action->getFieldT<IModelFieldRef>(0);
        comp->setRef(components.at(i%components.size()));
        IModelField *val1 = action->getField(1);
//        val1->val()->set_val_u(i);
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
    out_c->println("#include \"host_backend.h\"");

    IModelEvalIterator *activity_it = m_ctxt->mkModelEvalIterator(activities.get());
    IGeneratorEvalIteratorUP gen(m_factory->mkGeneratorMultiCoreSingleImageEmbCTest(
        {},
        -1,
        out_h.get(),
        out_c.get()
    ));

    gen->generate(comp.get(), activity_it);

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

TEST_F(TestComponentTree, resource_pools) {
    NameMap name_m;
    IModelActivityScopeUP activities(m_ctxt->mkModelActivityScope(ModelActivityScopeT::Sequence));
    std::vector<IModelFieldActionUP>   actions;

    m_ctxt->getDebugMgr()->enable(false);
    
    IDataTypeIntUP uint32(m_ctxt->mkDataTypeInt(false, 32));

    IDataTypeResource *rsrc_t = m_ctxt->mkDataTypeFlowObjT<IDataTypeResource>("rsrc_t", FlowObjKindE::Resource);
    rsrc_t->addField(m_ctxt->mkTypeFieldPhy("val", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    m_ctxt->addDataTypeFlowObj(rsrc_t);

    IDataTypeComponent *comp_sub_t = m_ctxt->mkDataTypeComponent("comp_sub_t");
    comp_sub_t->addField(m_ctxt->mkTypeFieldPhy("f1", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    comp_sub_t->addField(m_ctxt->mkTypeFieldPhy("f2", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    comp_sub_t->addField(m_ctxt->mkTypeFieldPool("rsrcs", rsrc_t, false, TypeFieldAttr::NoAttr, 4));
    m_ctxt->addDataTypeComponent(comp_sub_t);

    IDataTypeComponent *comp_t = m_ctxt->mkDataTypeComponent("comp_t");
    comp_t->addField(m_ctxt->mkTypeFieldPhy("c1", comp_sub_t, false, TypeFieldAttr::NoAttr, 0));
    comp_t->addField(m_ctxt->mkTypeFieldPhy("c2", comp_sub_t, false, TypeFieldAttr::NoAttr, 0));
    comp_t->addField(m_ctxt->mkTypeFieldPhy("c3", comp_sub_t, false, TypeFieldAttr::NoAttr, 0));
    m_ctxt->addDataTypeComponent(comp_t);

    IDataTypeAction *action_t = m_ctxt->mkDataTypeAction("comp_sub_t::action_t");
    action_t->addField(m_ctxt->mkTypeFieldPhy("val1", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    action_t->addField(m_ctxt->mkTypeFieldPhy("val2", uint32.get(), false, TypeFieldAttr::NoAttr, 0));
    action_t->setComponentType(comp_t);

    ITypeProcStmtScope *body = m_ctxt->mkTypeProcStmtScope();
    vsc::dm::IModelValUP val(m_ctxt->mkModelValU(5, 32));
    // body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("a", uint32.get(), false, 
    //     m_ctxt->mkTypeExprVal(val.get())));
    // val->set_val_u(10);
    // body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("b", uint32.get(), false, 
    //     m_ctxt->mkTypeExprVal(val.get())));
    body->addVariable(m_ctxt->mkTypeProcStmtVarDecl("c", uint32.get(), false, 0));
    body->addStatement(m_ctxt->mkTypeProcStmtAssign(
        m_ctxt->mkTypeExprFieldRef(
            ITypeExprFieldRef::RootRefKind::BottomUpScope, 0, {2} // c
        ),
        TypeProcStmtAssignOp::Eq,
        m_ctxt->mkTypeExprBin(
            m_ctxt->mkTypeExprFieldRef(
                ITypeExprFieldRef::RootRefKind::BottomUpScope, 0, {0} // a
            ),
            BinOp::Add,
            m_ctxt->mkTypeExprFieldRef(
                ITypeExprFieldRef::RootRefKind::BottomUpScope, 0, {1} // b
            ))
        )
    );
    val->set_val_u(1);
    // body->addStatement(m_ctxt->mkTypeProcStmtAssign(
    //     m_ctxt->mkTypeExprFieldRef(
    //         ITypeExprFieldRef::RootRefKind::TopDownScope, 0, {2} // val2
    //     ),
    //     TypeProcStmtAssignOp::Eq,
    //     m_ctxt->mkTypeExprBin(
    //         m_ctxt->mkTypeExprFieldRef(
    //             ITypeExprFieldRef::RootRefKind::TopDownScope, 0, {1} // val1
    //         ),
    //         BinOp::Add,
    //         m_ctxt->mkTypeExprVal(val.get())
    //         )
    //     )
    // );

    action_t->addExec(m_ctxt->mkTypeExecProc(ExecKindT::Body, body));
    action_t->setComponentType(comp_sub_t);
    comp_sub_t->addActionType(action_t);
    m_ctxt->addDataTypeAction(action_t);

    // TODO: add an exec body

    arl::dm::ModelBuildContext build_ctxt(m_ctxt.get());
    IModelFieldComponentRootUP comp(comp_t->mkRootFieldT<IModelFieldComponentRoot>(
        &build_ctxt,
        "pss_top",
        false));
    comp->initCompTree();

    std::vector<vsc::dm::IModelField *> components;
    for (uint32_t i=1; i<=3; i++) {
        components.push_back(comp->getField(i));
    }

    for (uint32_t i=0; i<16; i++) {
        IModelFieldAction *action = action_t->mkRootFieldT<IModelFieldAction>(
            &build_ctxt, "a", false);
        IModelFieldRef *comp = action->getFieldT<IModelFieldRef>(0);
        comp->setRef(components.at(i%components.size()));
        IModelField *val1 = action->getField(1);
//        val1->val()->set_val_u(i);
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
    out_c->println("#include \"host_backend.h\"");

    IModelEvalIterator *activity_it = m_ctxt->mkModelEvalIterator(activities.get());
    IGeneratorEvalIteratorUP gen(m_factory->mkGeneratorMultiCoreSingleImageEmbCTest(
        {},
        -1,
        out_h.get(),
        out_c.get()
    ));

    gen->generate(comp.get(), activity_it);

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
