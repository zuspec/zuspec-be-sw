/**
 * ITaskGenerateExecModelCustomGen.h
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
#include "zsp/arl/dm/ITypeExprMethodCallContext.h"
#include "zsp/arl/dm/ITypeExprMethodCallStatic.h"
#include "zsp/be/sw/IContext.h"
#include "zsp/be/sw/IOutput.h"
#include "IGenRefExpr.h"

namespace zsp {
namespace be {
namespace sw {

class TaskGenerateExecModel;

class ITaskGenerateExecModelCustomGen : 
    public virtual vsc::dm::IAssociatedData {
public:

    enum class Flags {
        None = 0,
        Builtin = (1 << 0)
    };

    virtual ~ITaskGenerateExecModelCustomGen() { }

    virtual void genExprMethodCallStaticB(
        IContext                            *ctxt,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallStatic  *call) = 0;

    virtual void genExprMethodCallStaticNB(
        IContext                            *ctxt,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallStatic  *call) = 0;

    virtual void genExprMethodCallContextB(
        IContext                            *ctxt,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallContext *call) = 0;

    virtual void genExprMethodCallContextNB(
        IContext                            *ctxt,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallContext *call) = 0;

    virtual void genDeclaration(
        IContext                            *ctxt,
        IOutput                             *out,
        vsc::dm::IDataType                  *type,
        bool                                fwd) = 0;

    virtual void genDefinition(
        IContext                            *ctxt,
        IOutput                             *out_h,
        IOutput                             *out_c,
        vsc::dm::IDataType                  *type) = 0;

    virtual bool hasFlags(Flags flags) = 0;

};

} /* namespace sw */
} /* namespace be */
} /* namespace zsp */


