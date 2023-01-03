/**
 * FunctionInfo.h
 *
 * Copyright 2022 Matthew Ballance and Contributors
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
#include "zsp/be/sw/IFunctionInfo.h"

namespace zsp {
namespace be {
namespace sw {


class FunctionInfo : public virtual IFunctionInfo {
public:
    FunctionInfo(
        arl::dm::IDataTypeFunction          *decl,
        const std::string                   &impl_name
    );

    virtual ~FunctionInfo();

    virtual const std::string &getImplName() const override {
        return m_impl_name;
    }

    virtual void setImplName(const std::string &n) override {
        m_impl_name = n;
    }

    virtual arl::dm::IDataTypeFunction *getDecl() const override {
        return m_decl;
    }

    virtual FunctionFlags getFlags() const override {
        return m_flags;
    }

    virtual void setFlags(FunctionFlags flags) override {
        m_flags = flags;
    }


private:
    std::string                     m_impl_name;
    arl::dm::IDataTypeFunction      *m_decl;
    FunctionFlags                   m_flags;

};

}
}
}


