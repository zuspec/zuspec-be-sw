/**
 * VisitorBase.h
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
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "IVisitor.h"

namespace zsp {
namespace be {
namespace sw {



class VisitorBase :
    public virtual arl::dm::VisitorBase,
    public virtual IVisitor {
public:
    VisitorBase();

    virtual ~VisitorBase();

    virtual void visitTypeProcStmtAsyncScope(TypeProcStmtAsyncScope *t) override;

    virtual void visitTypeProcStmtAsyncScopeGroup(TypeProcStmtAsyncScopeGroup *t) override;

    virtual void visitTypeProcStmtGotoAsyncScope(TypeProcStmtGotoAsyncScope *t) override;

};

}
}
}


