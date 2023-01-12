/**
 * TaskGenerateActionQueueCalls.h
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
#include "dmgr/IDebugMgr.h"
#include "zsp/arl/dm/IModelFieldComponentRoot.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "zsp/be/sw/IOutput.h"
#include "TaskBuildExecutorActionQueues.h"
#include "NameMap.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateActionQueueCalls : public arl::dm::VisitorBase {
public:
    TaskGenerateActionQueueCalls(
        dmgr::IDebugMgr                 *dmgr,
        NameMap                         *name_m,
        IModelFieldComponentRoot        *root
    );

    virtual ~TaskGenerateActionQueueCalls();

    void generate(
        IOutput                                     *out,
        const std::vector<ExecutorActionQueueEntry> &ops);

	virtual void visitModelField(vsc::dm::IModelField *f) override;

	virtual void visitModelFieldRef(vsc::dm::IModelFieldRef *f) override;

	virtual void visitModelFieldExecutor(arl::dm::IModelFieldExecutor *f) override;

	virtual void visitModelFieldExecutorClaim(IModelFieldExecutorClaim *f) override;

	virtual void visitDataTypeComponent(IDataTypeComponent *t) override;

	virtual void visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) override;

	virtual void visitDataTypeInt(vsc::dm::IDataTypeInt *t) override;

	virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

private:
    bool need_comma();

    void enter_field_scope();

    void leave_field_scope();

    void field_generated();

    bool is_first();

private:
    static dmgr::IDebug                     *m_dbg;
    dmgr::IDebugMgr                         *m_dmgr;
    IOutput                                 *m_out;
    NameMap                                 *m_name_m;
    IModelFieldComponentRoot                *m_root;
    std::string                             m_ctx_name;
    std::vector<vsc::dm::IModelField *>     m_field_s;
    std::vector<bool>                       m_isref_s;
    std::vector<int32_t>                    m_field_count_s;
    int32_t                                 m_field_count_last;

};

}
}
}


