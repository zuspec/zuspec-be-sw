/**
 * TaskCheckExecHasLoop.h
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

namespace zsp {
namespace be {
namespace sw {


class TaskCheckExecHasLoop :
    public virtual arl::dm::VisitorBase {
public:

    TaskCheckExecHasLoop() { }

    virtual ~TaskCheckExecHasLoop() { }

    bool check(arl::dm::ITypeProcStmt *s, bool recurse=false) {
        m_recurse = recurse;
        m_depth = 0;
        m_has = false;
        s->accept(m_this);
        return m_has;
    }

    virtual void visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *t) {
        if (!m_depth) {
            m_depth++;
            for (std::vector<arl::dm::ITypeProcStmtUP>::const_iterator
                it=t->getStatements().begin();
                it!=t->getStatements().end() && !m_has; it++) {
                (*it)->accept(m_this);
            }
            m_depth--;
        }
    }

	virtual void visitTypeProcStmtRepeat(arl::dm::ITypeProcStmtRepeat *s) override {
        m_has = true;
    }

	virtual void visitTypeProcStmtRepeatWhile(arl::dm::ITypeProcStmtRepeatWhile *s) override {
        m_has = true;
    }

    virtual void visitTypeProcStmtWhile(arl::dm::ITypeProcStmtWhile *t) {
        m_has = true;
    }

private:
    bool                    m_recurse;
    int32_t                 m_depth;
    bool                    m_has;

};

} /* namespace sw */
} /* namespace be */
} /* namespace zsp */


