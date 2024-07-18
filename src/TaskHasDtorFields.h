/**
 * TaskHasDtorFields.h
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
#include "dmgr/impl/DebugMacros.h"
#include "zsp/arl/dm/impl/VisitorBase.h"

namespace zsp {
namespace be {
namespace sw {



class TaskHasDtorFields :
    public arl::dm::VisitorBase {
public:

    TaskHasDtorFields(dmgr::IDebugMgr *dmgr) : m_dbg(0) { 
        DEBUG_INIT("zsp::be::sw::TaskHasDtorFields", dmgr);
    }

    virtual ~TaskHasDtorFields() { }

    bool check(vsc::dm::IDataType *t) {
        m_has = false;

        return m_has;
    }

	virtual void visitDataTypeAddrClaim(arl::dm::IDataTypeAddrClaim *t) override {
        DEBUG_ENTER("visitDataTypeAddrClaim");
        m_has = true;
        DEBUG_LEAVE("visitDataTypeAddrClaim");
    }

private:
    dmgr::IDebug            *m_dbg;
    bool                    m_has;

};

} /* namespace sw */
} /* namespace be */
} /* namespace zsp */


