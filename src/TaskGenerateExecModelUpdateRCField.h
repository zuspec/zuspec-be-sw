/**
 * TaskGenerateExecModelUpdateRCField.h
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
#include "IGenRefExpr.h"
#include "OutputExecScope.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateExecModelUpdateRCField :
    public virtual arl::dm::VisitorBase {
public:
    TaskGenerateExecModelUpdateRCField(
        IGenRefExpr         *refgen
    );

    virtual ~TaskGenerateExecModelUpdateRCField();

    virtual void generate_acquire(
        IOutput             *out,
        vsc::dm::IDataType  *type,
        vsc::dm::ITypeExpr  *expr);

    virtual void generate_acquire(
        IOutput                         *out,
        arl::dm::ITypeProcStmtVarDecl   *var);
        
    virtual void generate_release(
        IOutput             *out,
        vsc::dm::IDataType  *type,
        vsc::dm::ITypeExpr  *expr);

    virtual void generate_release(
        IOutput                         *out,
        arl::dm::ITypeProcStmtVarDecl   *var);
        
    virtual void generate_acquire_dtor(
        OutputExecScope                 *out,
        arl::dm::ITypeProcStmtVarDecl   *var);

    virtual void generate_dtor(
        OutputExecScope                 *out,
        arl::dm::ITypeProcStmtVarDecl   *var);

    virtual void visitDataTypeAddrHandle(arl::dm::IDataTypeAddrHandle *t) override;

private:
    enum Kind {
        Acquire,
        Release,
        AcquireDtor,
        Dtor
    };

private:
    Kind                            m_kind;
    IGenRefExpr                     *m_refgen;
    IOutput                         *m_out;
    OutputExecScope                 *m_out_s;
    vsc::dm::ITypeExpr              *m_expr;
    arl::dm::ITypeProcStmtVarDecl   *m_var;

};

}
}
}


