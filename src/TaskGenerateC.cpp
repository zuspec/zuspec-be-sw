/*
 * TaskGenerateC.cpp
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
#include "TaskGenerateC.h"
#include "TaskGenerateFunctionEmbeddedC.h"
#include "TaskGenerateFuncProtoEmbeddedC.h"
#include "TaskGenerateCPackedStruct.h"
#include "TaskGenerateEmbCRegGroup.h"
#include "TaskGenerateEmbCStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateC::TaskGenerateC(
    IContext                *ctxt,
    std::ostream            *csrc,
    std::ostream            *pub_h,
    std::ostream            *prv_h) : 
    m_ctxt(ctxt), m_csrc(csrc, false), 
    m_pub_h(pub_h, false), m_prv_h(prv_h, false) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateC", ctxt->getDebugMgr());
}

TaskGenerateC::~TaskGenerateC() {

}

void TaskGenerateC::generate(const std::vector<vsc::dm::IAccept *> &roots) {
    DEBUG_ENTER("generate");

    // TODO: Order the elements to generate according to dependencies

    for (std::vector<vsc::dm::IAccept *>::const_iterator
        it=roots.begin();
        it!=roots.end(); it++) {
        (*it)->accept(m_this);
    }
    DEBUG_LEAVE("generate");
}

void TaskGenerateC::visitDataTypeFunction(arl::dm::IDataTypeFunction *t) {
    if ((t->getFlags() & arl::dm::DataTypeFunctionFlags::Export) != arl::dm::DataTypeFunctionFlags::NoFlags) {
        // Emit to public header
        TaskGenerateFuncProtoEmbeddedC(m_ctxt).generate(&m_pub_h, t);
    } else {
        // Emit to private header
        TaskGenerateFuncProtoEmbeddedC(m_ctxt).generate(&m_prv_h, t);
    }

    if (t->getBody()) {
        // Define the function
        TaskGenerateFunctionEmbeddedC(m_ctxt).generate(&m_csrc, t);
    }

}

void TaskGenerateC::visitDataTypePackedStruct(arl::dm::IDataTypePackedStruct *t) {
    DEBUG_ENTER("visitDataTypePackedStruct %s", t->name().c_str());
    // TODO: determine whether this is an 'interface' type
    TaskGenerateCPackedStruct(m_ctxt).generate(&m_prv_h, t);
    DEBUG_LEAVE("visitDataTypePackedStruct %s", t->name().c_str());
}

void TaskGenerateC::visitDataTypeRegGroup(arl::dm::IDataTypeRegGroup *t) {
    DEBUG_ENTER("visitDataTypeRegGroup %s", t->name().c_str());
    TaskGenerateEmbCRegGroup(m_ctxt, &m_prv_h).generate(t);
    DEBUG_LEAVE("visitDataTypeRegGroup %s", t->name().c_str());
}

void TaskGenerateC::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeStruct %s", t->name().c_str());
    TaskGenerateEmbCStruct(m_ctxt, &m_prv_h).generate(t);
    DEBUG_LEAVE("visitDataTypeStruct %s", t->name().c_str());
}

dmgr::IDebug *TaskGenerateC::m_dbg = 0;

}
}
}
