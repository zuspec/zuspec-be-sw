/*
 * TaskGenerateComp.cpp
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
#include "TaskGenerateExecModel.h"
#include "TaskGenerateComp.h"
#include "TaskGenerateCompDoInit.h"
#include "TaskGenerateCompDoRunStart.h"
#include "TaskGenerateCompStruct.h"
#include "TaskGenerateExecModelCompExecInit.h"
#include "TaskGenerateCompInit.h"
#include "TaskGenerateCompStruct.h"
#include "TaskGenerateCompType.h"
#include "TaskGenerateExecBlockNB.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateComp::TaskGenerateComp(
    IContext    *ctxt,
    TypeInfo    *info,
    IOutput     *out_h,
    IOutput     *out_c) : TaskGenerateStruct(ctxt, info, out_h, out_c) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateComp", ctxt->getDebugMgr());
}

TaskGenerateComp::~TaskGenerateComp() {

}

void TaskGenerateComp::generate(vsc::dm::IDataTypeStruct *t) {
    m_out_h->println("#ifndef INCLUDED_%s_H", m_ctxt->nameMap()->getName(t).c_str());
    m_out_h->println("#define INCLUDED_%s_H", m_ctxt->nameMap()->getName(t).c_str());
    generate_header_includes(t, m_out_h);
    generate_header_typedefs(t, m_out_h);
    generate_data_type(t, m_out_h);
    generate_source_includes(t, m_out_c);
    generate_dtor(t, m_out_c);
    generate_exec_blocks(t, m_out_c);
    generate_do_init(t, m_out_h, m_out_c);
    TaskGenerateCompDoRunStart(m_ctxt, m_info, m_out_h, m_out_c).generate(t);
    generate_type(t, m_out_h, m_out_c);
    generate_init(t, m_out_h, m_out_c);
    m_out_h->println("#endif /* INCLUDED_%s_H */", m_ctxt->nameMap()->getName(t).c_str());
}

void TaskGenerateComp::generate_init(
        vsc::dm::IDataTypeStruct *t, 
        IOutput                 *out_h,
        IOutput                 *out_c) {
    TaskGenerateCompInit(m_ctxt, m_info, out_h, out_c).generate(t);
}

void TaskGenerateComp::generate_do_init(
        vsc::dm::IDataTypeStruct *t, 
        IOutput                 *out_h,
        IOutput                 *out_c) {
    TaskGenerateCompDoInit(m_ctxt, m_info, out_h, out_c).generate(t);
}

void TaskGenerateComp::generate_data_type(vsc::dm::IDataTypeStruct *t, IOutput *out) {
    DEBUG_ENTER("generate_type");
    TaskGenerateCompStruct(m_ctxt, m_info, out).generate(t);
    DEBUG_LEAVE("generate_type");
}

void TaskGenerateComp::generate_type(
        vsc::dm::IDataTypeStruct    *t, 
        IOutput                     *out_h,
        IOutput                     *out_c) {
    TaskGenerateCompType(m_ctxt, out_h, out_c).generate(t);
}

void TaskGenerateComp::generate_exec_blocks(vsc::dm::IDataTypeStruct *t, IOutput *out) {
    DEBUG_ENTER("generate_exec_blocks");
    arl::dm::IDataTypeArlStruct *arl_t = dynamic_cast<arl::dm::IDataTypeArlStruct *>(t);

    if (arl_t) {
        std::vector<arl::dm::ExecKindT> kinds = {
            arl::dm::ExecKindT::InitDown,
            arl::dm::ExecKindT::InitUp
        };
        std::vector<std::string> names = {
            "init_down",
            "init_up"
        };
        GenRefExprExecModel refgen(m_ctxt->getDebugMgr(), t, "this_p", true);

        for (auto kind = kinds.begin(); kind != kinds.end(); kind++) {
            const std::vector<arl::dm::ITypeExecUP> &execs = arl_t->getExecs(*kind);
            std::string tname = m_ctxt->nameMap()->getName(t);
            std::string fname = m_ctxt->nameMap()->getName(t) + "__" + names[(int)(kind-kinds.begin())];
            TaskGenerateExecBlockNB(m_ctxt, &refgen, m_out_c).generate(
                fname,
                tname,
                execs);
        }
    }
    DEBUG_LEAVE("generate_exec_blocks");
}

// void TaskGenerateComp::generate(arl::dm::IDataTypeComponent *comp_t) {
//     DEBUG_ENTER("generate");

//     // Generate the component struct
// //    TaskGenerateExecModelCompStruct(m_gen, m_gen->getOutHPrv()).generate(comp_t);

//     TaskGenerateExecModelCompInit(m_gen).generate(comp_t);

//     TaskGenerateExecModelCompExecInit(m_gen, m_gen->getOutC()).generate(comp_t);

// /*
//     // First, handle forward declaration
//     m_mode = Mode::FwdDecl;
//     comp_t->accept(m_this);

//     m_mode = Mode::Decl;
//     comp_t->accept(m_this);
//  */

//     DEBUG_LEAVE("generate");
// }

// void TaskGenerateComp::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
//     DEBUG_ENTER("visitDataTypeComponent");

//     switch (m_mode) {
//         case Mode::FwdDecl: {
//             if (!m_gen->fwdDecl(t)) {
//                 // Go ahead and forward-declare 
//                 /*
//                 TaskGenerateFwdDecl(
//                     m_gen->getDebugMgr(),
//                     m_gen->getNameMap(),
//                     m_gen->getOutHPrv()).generate(t);
//                  */
//                 m_gen->getOutHPrv()->println("static void %s_init(struct %s_s *actor, struct %s_s *obj);",
//                     m_gen->getNameMap()->getName(t).c_str(),
//                     m_gen->getActorName().c_str(),
//                     m_gen->getNameMap()->getName(t).c_str());
//             }

//             // Recurse to find other 
//             for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
//                 it=t->getFields().begin();
//                 it!=t->getFields().end(); it++) {
//                 (*it)->accept(m_this);
//             }
//         } break;

//         case Mode::Decl: {
//             std::unordered_set<vsc::dm::IDataType *>::const_iterator it;

//             if ((it=m_decl_s.find(t)) == m_decl_s.end()) {
//                 m_decl_s.insert(t);

//                 // Recurse first, such that we get dependencies covered before they're used
//                 for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
//                     it=t->getFields().begin();
//                     it!=t->getFields().end(); it++) {
//                     (*it)->accept(m_this);
//                 }

// //                TaskGenerateExecModelCompStruct(m_gen).generate(t);

//                 TaskGenerateExecModelCompInit(m_gen).generate(t);


//             }
//         } break;
//     }

//     DEBUG_LEAVE("visitDataTypeComponent");
// }

dmgr::IDebug *TaskGenerateComp::m_dbg = 0;

}
}
}
