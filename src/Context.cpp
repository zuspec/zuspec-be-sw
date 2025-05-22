/*
 * Context.cpp
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
#include <string.h>
#include "Context.h"
#include "TaskGetExecScopeVarInfo.h"
#include "TaskInitContextC.h"


namespace zsp {
namespace be {
namespace sw {

Context::Context(
    dmgr::IDebugMgr         *dmgr,
    arl::dm::IContext       *ctxt) : m_dmgr(dmgr), m_ctxt(ctxt) {
    TaskInitContextC(dmgr).init(ctxt);

    // Find core functions
    memset(m_backend_funcs, 0, sizeof(m_backend_funcs));
    m_backend_funcs[(int)BackendFunctions::Printf] = ctxt->findDataTypeFunction("printf");
    m_backend_funcs[(int)BackendFunctions::Read8] = ctxt->findDataTypeFunction("addr_reg_pkg::read8");
    m_name_m.setName(m_backend_funcs[(int)BackendFunctions::Read8], "read8");
    m_backend_funcs[(int)BackendFunctions::Write8] = ctxt->findDataTypeFunction("addr_reg_pkg::write8");
    m_name_m.setName(m_backend_funcs[(int)BackendFunctions::Write8], "write8");
    m_backend_funcs[(int)BackendFunctions::Read16] = ctxt->findDataTypeFunction("addr_reg_pkg::read16");
    m_name_m.setName(m_backend_funcs[(int)BackendFunctions::Read16], "read16");
    m_backend_funcs[(int)BackendFunctions::Write16] = ctxt->findDataTypeFunction("addr_reg_pkg::write16");
    m_name_m.setName(m_backend_funcs[(int)BackendFunctions::Write16], "write16");
    m_backend_funcs[(int)BackendFunctions::Read32] = ctxt->findDataTypeFunction("addr_reg_pkg::read32");
    m_name_m.setName(m_backend_funcs[(int)BackendFunctions::Read32], "read32");
    m_backend_funcs[(int)BackendFunctions::Write32] = ctxt->findDataTypeFunction("addr_reg_pkg::write32");
    m_name_m.setName(m_backend_funcs[(int)BackendFunctions::Write32], "write32");
    m_backend_funcs[(int)BackendFunctions::Read64] = ctxt->findDataTypeFunction("addr_reg_pkg::read64");
    m_name_m.setName(m_backend_funcs[(int)BackendFunctions::Read64], "read64");
    m_backend_funcs[(int)BackendFunctions::Write64] = ctxt->findDataTypeFunction("addr_reg_pkg::write64");
    m_name_m.setName(m_backend_funcs[(int)BackendFunctions::Write64], "write64");

    /*
    for (uint32_t i=0; i<sizeof(m_backend_funcs)/sizeof(arl::dm::IDataTypeFunction *); i++) {
        fprintf(stdout, "Function[%d]: %p", i, m_backend_funcs[i]);
    }
     */
}

Context::~Context() {

}

void Context::pushTypeScope(vsc::dm::IDataTypeStruct *t) {
    m_typescope_s.push_back(t);
}

vsc::dm::IDataTypeStruct *Context::typeScope() {
    return (m_typescope_s.size())?m_typescope_s.back():0;
}

void Context::popTypeScope() {
    m_typescope_s.pop_back();
}

void Context::pushExecScope(vsc::dm::IAccept *s) {
    m_execscope_s.push_back(s);
}

vsc::dm::IAccept *Context::execScope(int32_t off) {
    return (off<m_execscope_s.size())?m_execscope_s.at(m_execscope_s.size()-off-1):0;
}

ExecScopeVarInfo Context::execScopeVar(
        int32_t     scope_off,
        int32_t     var_off) {
    if (scope_off < m_execscope_s.size()) {
        return TaskGetExecScopeVarInfo().get(
            m_execscope_s.at(m_execscope_s.size()-scope_off-1), 
            var_off);
    } else {
        return {.var=0, .flags=ExecScopeVarFlags::NoFlags};
    }
}

void Context::popExecScope() {
    m_execscope_s.pop_back();
}

}
}
}
