/**
 * TaskGenerateExecModelCustomGenBase.h
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
#include "ITaskGenerateExecModelCustomGen.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateExecModelCustomGenBase :
    public virtual ITaskGenerateExecModelCustomGen {
public:
    TaskGenerateExecModelCustomGenBase(
        dmgr::IDebugMgr     *dmgr
    );

    virtual ~TaskGenerateExecModelCustomGenBase();

    virtual void genExprMethodCallStaticB(
        TaskGenerateExecModel               *gen,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallStatic  *call) override;

    virtual void genExprMethodCallStaticNB(
        TaskGenerateExecModel               *gen,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallStatic  *call) override;

    virtual void genExprMethodCallContextB(
        TaskGenerateExecModel               *gen,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallContext *call) override;

    virtual void genExprMethodCallContextNB(
        TaskGenerateExecModel               *gen,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallContext *call) override;

    virtual void genFwdDecl(
        TaskGenerateExecModel               *gen,
        IOutput                             *out,
        vsc::dm::IDataType                  *type) override;

    virtual void genDefinition(
        TaskGenerateExecModel               *gen,
        IOutput                             *out_h,
        IOutput                             *out_c,
        vsc::dm::IDataType                  *type) override;

protected:
    dmgr::IDebug                *m_dbg;

};

}
}
}


