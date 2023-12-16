/**
 * TaskGenerateC.h
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
#include "NameMap.h"
#include "Output.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateC : public virtual arl::dm::VisitorBase {
public:
    TaskGenerateC(
        IContext                *ctxt,
        std::ostream            *csrc,
        std::ostream            *pub_h,
        std::ostream            *prv_h);

    virtual ~TaskGenerateC();

    void generate(const std::vector<vsc::dm::IAccept *> &roots);

	virtual void visitDataTypeFunction(arl::dm::IDataTypeFunction *t) override;

	virtual void visitDataTypePackedStruct(arl::dm::IDataTypePackedStruct *t) override;

	virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

private:
    static dmgr::IDebug         *m_dbg;
    IContext                    *m_ctxt;
    Output                      m_csrc;
    Output                      m_pub_h;
    Output                      m_prv_h;

};

}
}
}


