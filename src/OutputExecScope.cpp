/*
 * OutputExecScope.cpp
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
#include "OutputExecScope.h"


namespace zsp {
namespace be {
namespace sw {


OutputExecScope::OutputExecScope(
        bool                new_scope,
        const std::string   &ind) : 
        m_new_scope(new_scope), m_decl(ind), m_exec(ind) {
    if (new_scope) {
        m_decl.inc_ind();
        m_exec.inc_ind();
    }
}

OutputExecScope::OutputExecScope(
        bool                new_scope,
        IOutput             *upper) :
        m_new_scope(new_scope), m_decl(upper->ind()), m_exec(upper->ind()) {
    
    // If we'll be creating a new scope, add an additional level of indent
    if (new_scope) {
        m_decl.inc_ind();
        m_exec.inc_ind();
    }
}

OutputExecScope::~OutputExecScope() {

}

void OutputExecScope::apply(IOutput *out) {
    if (m_new_scope) {
        out->println("{");
        out->inc_ind();
    }
    out->writes(m_decl.getValue());
    out->writes("\n");
    out->writes(m_exec.getValue());

    if (m_new_scope) {
        out->dec_ind();
        out->println("}");
    }
}

}
}
}
