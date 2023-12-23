/**
 * Context.h
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
#include "zsp/arl/dm/IDataTypeFunction.h"
#include "zsp/be/sw/IContext.h"
#include "NameMap.h"

namespace zsp {
namespace be {
namespace sw {


class Context : public virtual IContext {
public:
    Context(
        dmgr::IDebugMgr         *dmgr,
        arl::dm::IContext       *ctxt);

    virtual ~Context();

    virtual dmgr::IDebugMgr *getDebugMgr() const override {
        return m_dmgr;
    }

    virtual arl::dm::IContext *ctxt() const override {
        return m_ctxt;
    }

    virtual INameMap *nameMap() override {
        return &m_name_m;
    }

    virtual arl::dm::IDataTypeFunction *getBackendFunction(
        BackendFunctions    func) override {
        return m_backend_funcs[(int)func];
    }

    void setBackendFunction(
        BackendFunctions                id,
        zsp::arl::dm::IDataTypeFunction *func) {
        m_backend_funcs[(int)id] = func;
    }

    virtual void pushTypeScope(vsc::dm::IDataTypeStruct *t) override;

    virtual vsc::dm::IDataTypeStruct *typeScope() override;

    virtual void popTypeScope() override;

    virtual void pushExecScope(vsc::dm::IAccept *s) override;

    virtual vsc::dm::IAccept *execScope(int32_t off=0) override;

    virtual ExecScopeVarInfo execScopeVar(
        int32_t     scope_off,
        int32_t     var_off) override;

    virtual void popExecScope() override;

private:
    dmgr::IDebugMgr                                 *m_dmgr;
    arl::dm::IContext                               *m_ctxt;
    NameMap                                         m_name_m;
    arl::dm::IDataTypeFunction                      *m_backend_funcs[(int)BackendFunctions::NumFuncs];
    std::vector<vsc::dm::IDataTypeStruct *>         m_typescope_s;
    std::vector<vsc::dm::IAccept *>                 m_execscope_s;
};

}
}
}
