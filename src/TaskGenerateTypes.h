/**
 * TaskGenerateTypes.h
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
#include <set>
#include <string>
#include "dmgr/IDebugMgr.h"
#include "zsp/be/sw/IContext.h"
#include "zsp/arl/dm/impl/VisitorBase.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateTypes :
    public virtual arl::dm::VisitorBase {
public:
    TaskGenerateTypes(IContext *ctxt, const std::string &outdir);

    virtual ~TaskGenerateTypes();

    virtual void generate(vsc::dm::IDataTypeStruct *root);

    virtual void visitDataTypeArlStruct(arl::dm::IDataTypeArlStruct *t) override;

    virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

private:
    bool mkpath(const std::string &path);
    static dmgr::IDebug                     *m_dbg;
    IContext                                *m_ctxt;
    std::string                             m_outdir;
    std::set<vsc::dm::IDataTypeStruct *>    m_types;

};

}
}
}
