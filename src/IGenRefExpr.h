/**
 * IGenRefExpr.h
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
#include "vsc/dm/ITypeExprRef.h"
#include "zsp/arl/dm/ITypeProcStmtScope.h"

namespace zsp {
namespace be {
namespace sw {



class IGenRefExpr {
public:

    virtual ~IGenRefExpr() { }

    virtual std::string genLval(vsc::dm::ITypeExpr *ref) = 0;

    virtual std::string genRval(vsc::dm::ITypeExpr *ref) = 0;

    virtual bool isFieldRefExpr(vsc::dm::ITypeExpr *ref) = 0;

    virtual bool isRefFieldRefExpr(vsc::dm::ITypeExpr *ref) = 0;

    virtual bool isRefCountedField(vsc::dm::IAccept *ref) = 0;

    virtual void pushScope(arl::dm::ITypeProcStmtScope *s) = 0;

    virtual void popScope() = 0;

};

} /* namespace sw */
} /* namespace be */
} /* namespace zsp */


