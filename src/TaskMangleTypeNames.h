/**
 * TaskMangleTypeNames.h
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
#include "vsc/dm/IDataTypeStruct.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "NameMap.h"

namespace zsp {
namespace be {
namespace sw {

class TaskMangleTypeNames : public virtual arl::dm::VisitorBase {
public:
    TaskMangleTypeNames(
        dmgr::IDebugMgr     *dmgr, 
        NameMap             *name_m);

    virtual ~TaskMangleTypeNames();

    void mangle(vsc::dm::IDataTypeStruct *t);

	virtual void visitDataTypeAction(arl::dm::IDataTypeAction *i) override;

	virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;

private:
    static dmgr::IDebug     *m_dbg;
    NameMap                 *m_name_m;

};

}
}
}


