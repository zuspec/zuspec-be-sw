/**
 * TaskGenerateExecModel.h
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
#include <unordered_set>
#include "dmgr/IDebugMgr.h"
#include "zsp/be/sw/IOutput.h"
#include "zsp/arl/dm/IContext.h"
#include "zsp/arl/dm/IDataTypeComponent.h"
#include "zsp/arl/dm/IDataTypeAction.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "zsp/be/sw/INameMap.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateExecModel {
public:
    TaskGenerateExecModel(
        arl::dm::IContext               *ctxt);

    virtual ~TaskGenerateExecModel();

    dmgr::IDebugMgr *getDebugMgr() const { return m_dmgr; }

    void generate(
        arl::dm::IDataTypeComponent     *comp_t,
        arl::dm::IDataTypeAction        *action_t,
        std::ostream                    *out_c,
        std::ostream                    *out_h,
        std::ostream                    *out_h_prv);

    const std::string &getActorName() const {
        return m_actor_name;
    }

    /**
     */
    bool fwdDecl(vsc::dm::IDataType *dt, bool add=true);

    arl::dm::IContext *getContext() { return m_ctxt; }

    INameMap *getNameMap() { return m_name_m.get(); }

    IOutput *getOutC() { return m_out_c.get(); }

    IOutput *getOutH() { return m_out_h.get(); }

    IOutput *getOutHPrv() { return m_out_h_prv.get(); }

private:
    void generate_actor_entry();

    void attach_custom_gen();

private:
    static dmgr::IDebug                         *m_dbg;
    arl::dm::IContext                           *m_ctxt;
    dmgr::IDebugMgr                             *m_dmgr;
    arl::dm::IDataTypeComponent                 *m_comp_t;
    arl::dm::IDataTypeAction                    *m_action_t;
    IOutputUP                                   m_out_c;
    IOutputUP                                   m_out_h;
    IOutputUP                                   m_out_h_prv;
    std::string                                 m_actor_name;
    INameMapUP                                  m_name_m;

    std::unordered_set<vsc::dm::IDataType *>    m_dt_fwd_decl;

};

}
}
}


