/**
 * TaskGenerateEmbCStruct.h
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
#pragma once
#include <set>
#include "dmgr/IDebugMgr.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "zsp/be/sw/IOutput.h"
#include "NameMap.h"
#include "TaskMangleTypeNames.h"

namespace zsp {
namespace be {
namespace sw {

class TaskGenerateEmbCStruct : public arl::dm::VisitorBase {
public:
    TaskGenerateEmbCStruct(
        dmgr::IDebugMgr         *dmgr,
        IOutput                 *out,
        NameMap                 *name_m);

    virtual ~TaskGenerateEmbCStruct();

    void generate(vsc::dm::IDataTypeStruct *type);

    // We do not generate action-type fields
	virtual void visitDataTypeAction(arl::dm::IDataTypeAction *i) override {}

	virtual void visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) override;

	virtual void visitDataTypeInt(vsc::dm::IDataTypeInt *t) override;

	virtual void visitDataTypeResource(arl::dm::IDataTypeResource *t) override;

	virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

	virtual void visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) override;

	virtual void visitTypeFieldPool(arl::dm::ITypeFieldPool *f) override;

	virtual void visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) override;

	virtual void visitTypeFieldExecutor(arl::dm::ITypeFieldExecutor *f) override;

private:
    static dmgr::IDebug                     *m_dbg;
    uint32_t                                m_depth;
    TaskMangleTypeNames                     m_mangler;
    IOutput                                 *m_out;
    NameMap                                 *m_name_m;
    std::vector<vsc::dm::ITypeField *>      m_field_s;
    std::vector<bool>                       m_ref_s;
    std::vector<std::set<std::string> *>    m_ignore_field_s;

    static std::set<std::string>            m_ignore_resource_fields;

};

}
}
}


