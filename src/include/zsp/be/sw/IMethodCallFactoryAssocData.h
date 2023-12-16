/**
 * IMethodCallFactoryAssocData.h
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
#include "vsc/dm/IAssociatedData.h"
#include "zsp/arl/dm/IContext.h"
#include "zsp/arl/dm/ITypeExprMethodCallContext.h"
#include "zsp/arl/dm/ITypeExprMethodCallStatic.h"
#include "zsp/be/sw/IContext.h"

namespace zsp {
namespace be {
namespace sw {



class IMethodCallFactoryAssocData : public virtual vsc::dm::IAssociatedData {
public:

    virtual ~IMethodCallFactoryAssocData() { }

    virtual vsc::dm::ITypeExpr *mkCallContext(
        IContext                            *ctxt,
        arl::dm::ITypeExprMethodCallContext *call
    ) = 0;

    virtual vsc::dm::ITypeExpr *mkCallStatic(
        IContext                            *ctxt,
        arl::dm::ITypeExprMethodCallStatic  *call
    ) = 0;

};

} /* namespace sw */
} /* namespace be */
} /* namespace zsp */


