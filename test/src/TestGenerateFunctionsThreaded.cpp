/*
 * TestGenerateFunctionsThreaded.cpp
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
#include "vsc/dm/IDataTypeInt.h"
#include "TestGenerateFunctionsThreaded.h"

using namespace vsc::dm;
using namespace zsp::arl::dm;

namespace zsp {
namespace be {
namespace sw {


TestGenerateFunctionsThreaded::TestGenerateFunctionsThreaded() {

}

TestGenerateFunctionsThreaded::~TestGenerateFunctionsThreaded() {

}

TEST_F(TestGenerateFunctionsThreaded, smoke) {
    NameMap name_m;

    IDataTypeIntUP uint32(m_ctxt->mkDataTypeInt(false, 32));
    IDataTypeFunctionUP my_func(m_ctxt->mkDataTypeFunction("my_func", uint32.get(), false));
    my_func->addParameter(m_ctxt->mkDataTypeFunctionParamDecl(
        "a",
        ParamDir::In,
        uint32.get(),
        false,
        0));
    my_func->addParameter(m_ctxt->mkDataTypeFunctionParamDecl(
        "b",
        ParamDir::In,
        uint32.get(),
        false,
        0));

    my_func->getBody()->addVariable(
        m_ctxt->mkTypeProcStmtVarDecl("v1", uint32.get(), false, 0));
    IModelVal *val = m_ctxt->mkModelVal();
    val->setBits(32);
    val->set_val_u(25);
    my_func->getBody()->addStatement(
        m_ctxt->mkTypeProcStmtAssign(
            m_ctxt->mkTypeExprFieldRef(
                ITypeExprFieldRef::RootRefKind::BottomUpScope, 0, {0} // v1
            ),
            TypeProcStmtAssignOp::Eq,
            m_ctxt->mkTypeExprBin(
                m_ctxt->mkTypeExprFieldRef(
                    ITypeExprFieldRef::RootRefKind::BottomUpScope, 1, {0} // a
                ),
                vsc::dm::BinOp::Add,
                m_ctxt->mkTypeExprFieldRef(
                    ITypeExprFieldRef::RootRefKind::BottomUpScope, 1, {1} // b
                )
            )
        )
    );
    my_func->getBody()->addVariable(
        m_ctxt->mkTypeProcStmtVarDecl("v2", uint32.get(), false, 0));

    my_func->getBody()->addStatement(
        m_ctxt->mkTypeProcStmtReturn(
            m_ctxt->mkTypeExprFieldRef(
                ITypeExprFieldRef::RootRefKind::BottomUpScope, 0, {0} // v1
            )
        )
    );

    IOutputUP out_c;
    IOutputUP out_h;

    ASSERT_TRUE((out_c = IOutputUP(openOutput("test.c"))));
    ASSERT_TRUE((out_h = IOutputUP(openOutput("test.h"))));

    out_c->println("#include <stdio.h>");
    out_c->println("#include \"test.h\"");

    IGeneratorFunctionsUP funcs_gen(m_factory->mkGeneratorFunctionsThreaded());
    std::vector<arl::dm::IDataTypeFunction *> funcs;
    std::vector<std::string> inc_h, inc_c;

    funcs.push_back(my_func.get());

    funcs_gen->generate(
        m_ctxt.get(),
        funcs,
        inc_c,
        inc_h,
        out_c.get(),
        out_h.get()
    );

    out_c->println("int main() {");
    out_c->inc_ind();
    out_c->println("unsigned int r;");
    for (uint32_t i=0; i<10; i++) {
        for (uint32_t j=0; j<10; j++) {
            out_c->println("r = my_func(%d, %d);", i, j);
            out_c->println("fprintf(stdout, \"%%s\\n\"\, (r == %d)?\"PASSED\":\"FAILED\");", (i+j));
        }
    }
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
