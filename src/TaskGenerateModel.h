/**
 * TaskGenerateModel.h
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
#pragma once
#include "dmgr/IDebugMgr.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "zsp/be/sw/IContext.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateModel :
    public virtual arl::dm::VisitorBase {
public:
    TaskGenerateModel(
        IContext                        *ctxt,
        const std::string               &outdir);

    virtual ~TaskGenerateModel();

    virtual void generate(
        arl::dm::IDataTypeComponent *pss_top,
        const std::vector<arl::dm::IDataTypeAction *> &actions);

    virtual void visitDataTypeAction(arl::dm::IDataTypeAction *t) override;

    virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;


protected:
    void attach_custom_gen();

    void generate_interface();
        
    void generate_api();

    enum class mode_e {
        COUNT,
        INCLUDE,
        GETTYPE
    };
    enum class kind_e {
        ACTION,
        COMPONENT,
        BOTH
    };

private:
    static dmgr::IDebug             *m_dbg;
    IContext                        *m_ctxt;
    std::string                     m_outdir;
    std::string                     m_model_name;
    mode_e                          m_mode;
    kind_e                          m_kind;
    int32_t                         m_count;
    IOutput                         *m_out;

};

}
}
}


