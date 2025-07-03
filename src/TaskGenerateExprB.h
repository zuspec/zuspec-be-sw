/**
 * TaskGenerateExprB.h
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
#include "TaskGenerateExprNB.h"

namespace zsp {
namespace be {
namespace sw {


/**
 * Generating expressions in blocking contexts is *almost* the
 * same as generating expressions in a non-blocking context. 
 * Primary difference is how calls are handled
 */
class TaskGenerateExprB :
    public virtual TaskGenerateExprNB {
public:
    TaskGenerateExprB(
        IContext                    *ctxt,  
        IGenRefExpr                 *refgen,
        IOutput                     *out
    );

    virtual ~TaskGenerateExprB();

    virtual void visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) override;

    virtual void visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) override;

};

}
}
}


