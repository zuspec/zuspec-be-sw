/**
 * IContext.h
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
#include "zsp/arl/dm/IContext.h"
#include "zsp/be/sw/INameMap.h"

namespace zsp {
namespace be {
namespace sw {

enum class BackendFunctions {
    Printf,
    Read8,
    Read16,
    Read32,
    Read64,
    Write8,
    Write16,
    Write32,
    Write64,
    NumFuncs
};

enum class ExecScopeVarFlags {
    NoFlags = 0,
    IsPtr = (1 << 0)
};

static inline ExecScopeVarFlags operator | (const ExecScopeVarFlags lhs, const ExecScopeVarFlags rhs) {
	return static_cast<ExecScopeVarFlags>(
			static_cast<uint32_t>(lhs) | static_cast<uint32_t>(rhs));
}

static inline ExecScopeVarFlags operator & (const ExecScopeVarFlags lhs, const ExecScopeVarFlags rhs) {
	return static_cast<ExecScopeVarFlags>(
			static_cast<uint32_t>(lhs) & static_cast<uint32_t>(rhs));
}

static inline ExecScopeVarFlags operator ~ (const ExecScopeVarFlags lhs) {
	return static_cast<ExecScopeVarFlags>(~static_cast<uint32_t>(lhs));
}

struct ExecScopeVarInfo {
    arl::dm::ITypeProcStmtVarDecl       *var;
    ExecScopeVarFlags                   flags;
};

class IContext {
public:

    virtual ~IContext() { }

    virtual dmgr::IDebugMgr *getDebugMgr() const = 0;

    virtual arl::dm::IContext *ctxt() const = 0;

    virtual INameMap *nameMap() = 0;

    virtual arl::dm::IDataTypeFunction *getBackendFunction(
        BackendFunctions    func) = 0;

    virtual void pushTypeScope(vsc::dm::IDataTypeStruct *t) = 0;

    virtual vsc::dm::IDataTypeStruct *typeScope() = 0;

    virtual void popTypeScope() = 0;

    virtual void pushExecScope(vsc::dm::IAccept *s) = 0;

    virtual vsc::dm::IAccept *execScope(int32_t off=0) = 0;

    virtual ExecScopeVarInfo execScopeVar(
        int32_t     scope_off,
        int32_t     var_off) = 0;

    virtual void popExecScope() = 0;

};

}
}
}

