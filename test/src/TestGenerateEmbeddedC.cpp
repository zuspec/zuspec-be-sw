/*
 * TestGenerateEmbeddedC.cpp
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
#include "OutputStr.h"
#include "TestGenerateEmbeddedC.h"
#include "TaskGenerateFunctionEmbeddedC.h"
#include "TaskGenerateFuncProtoEmbeddedC.h"

using namespace zsp::arl::dm;
using namespace vsc::dm;

namespace zsp {
namespace be {
namespace sw {


TestGenerateEmbeddedC::TestGenerateEmbeddedC() {

}

TestGenerateEmbeddedC::~TestGenerateEmbeddedC() {

}

TEST_F(TestGenerateEmbeddedC, smoke) {
    IDataTypeFunctionUP my_func(m_ctxt->mkDataTypeFunction("my_func", 0, false));
    NameMap name_m;
    OutputStr out_decl("");
    OutputStr out_def("");

    IDataTypeIntUP uint32(m_ctxt->mkDataTypeInt(false, 32));
    my_func->addParameter(m_ctxt->mkTypeProcStmtVarDecl("a", uint32.get(), false, 0));
    my_func->addParameter(m_ctxt->mkTypeProcStmtVarDecl("b", uint32.get(), false, 0));

    my_func->getBody()->addStatement(
        m_ctxt->mkTypeProcStmtVarDecl("v1", uint32.get(), false, 0));
    ITypeExprFieldRef *ref = m_ctxt->mkTypeExprFieldRef();
    IModelVal *val = m_ctxt->mkModelVal();
    val->setBits(32);
    val->set_val_u(25);
    ref->addActiveScopeRef(0);
    my_func->getBody()->addStatement(
        m_ctxt->mkTypeProcStmtAssign(
            ref,
            TypeProcStmtAssignOp::Eq,
            m_ctxt->mkTypeExprVal(val)
        ));
    my_func->getBody()->addStatement(
        m_ctxt->mkTypeProcStmtVarDecl("v2", uint32.get(), false, 0));

/*
    my_func->getBody()->addStatement(
        m_ctxt->mkTypeProcStmtIfElse(
            m_ctxt->mkTypeExprBin(
                m_
            )

        )
    )
 */

    TaskGenerateFuncProtoEmbeddedC(&name_m).generate(
        &out_decl,
        my_func.get()
    );

    TaskGenerateFunctionEmbeddedC(&name_m).generate(
        &out_def,
        my_func.get()
    );

    fprintf(stdout, "Declaration:\n%s\n", out_decl.getValue().c_str());
    fprintf(stdout, "Definition:\n%s\n", out_def.getValue().c_str());

}

}
}
}
