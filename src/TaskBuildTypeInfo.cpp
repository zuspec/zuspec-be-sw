/*
 * TaskBuildTypeInfo.cpp
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
#include <algorithm>
#include "dmgr/impl/DebugMacros.h"
#include "TaskBuildTypeInfo.h"


namespace zsp {
namespace be {
namespace sw {

TaskBuildTypeInfo::TaskBuildTypeInfo(IContext *ctxt) : 
    m_ctxt(ctxt), m_depth(0), m_is_ref(false) {
    DEBUG_INIT("zsp::be::sw::TaskBuildTypeInfo", ctxt->getDebugMgr());
}

TaskBuildTypeInfo::~TaskBuildTypeInfo() {

}

TypeInfo *TaskBuildTypeInfo::build(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("build %s", t->name().c_str());
    m_type_info = TypeInfoUP(new TypeInfo(t));
    t->accept(this);
    DEBUG_LEAVE("build %s", t->name().c_str());
    return m_type_info.release();
}

void TaskBuildTypeInfo::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeStruct %s", t->name().c_str());

    if (m_depth == 0) {
        if (t->getSuper()) {
            m_type_info->addReferencedValType(t->getSuper());
        }
        m_depth++;
        for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
            it=t->getFields().begin()+(t->getSuper()?t->getSuper()->getFields().size():0); 
            it!=t->getFields().end(); it++) {
            (*it)->accept(this);
        }
        m_depth--;
    } else {
        if (m_is_ref) {
            m_type_info->addReferencedRefType(t);
        } else {
            m_type_info->addReferencedValType(t);
        }
    }

    DEBUG_LEAVE("visitDataTypeStruct %s", t->name().c_str());   
}

void TaskBuildTypeInfo::visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) {
    DEBUG_ENTER("visitTypeFieldPhy %s", f->name().c_str());
    m_is_ref = false;
    f->getDataType()->accept(this);
    DEBUG_LEAVE("visitTypeFieldPhy %s", f->name().c_str());
}

void TaskBuildTypeInfo::visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) {
    DEBUG_ENTER("visitTypeFieldRef %s", f->name().c_str());
    m_is_ref = true;
    f->getDataType()->accept(this);
    DEBUG_LEAVE("visitTypeFieldRef %s", f->name().c_str());
}

dmgr::IDebug *TaskBuildTypeInfo::m_dbg = 0;

}
}
}
