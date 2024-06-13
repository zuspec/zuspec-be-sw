/*
 * TaskBuildImplFunction.cpp
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
#include "TaskBuildImplFunction.h"


namespace zsp {
namespace be {
namespace sw {


TaskBuildImplFunction::TaskBuildImplFunction() {

}

TaskBuildImplFunction::~TaskBuildImplFunction() {

}

ImplFunctionData *TaskBuildImplFunction::build(arl::dm::IDataTypeFunction *func) {
    m_impl = ImplFunctionDataUP(new ImplFunctionData());
    func->accept(m_this);
    return m_impl.release();
}

void TaskBuildImplFunction::visitDataTypeFunction(arl::dm::IDataTypeFunction *t) {

    // TODO: add a field for return value

    // TODO: add fields for each parameter

    for (std::vector<arl::dm::ITypeProcStmtUP>::const_iterator
        it=t->getBody()->getStatements().begin();
        it!=t->getBody()->getStatements().end(); it++) {
        (*it)->accept(m_this);
    }
}

}
}
}
