/**
 * NameMap.h
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
#include <memory>
#include <string>
#include <unordered_map>
#include "zsp/arl/dm/IDataTypeFunction.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "zsp/be/sw/INameMap.h"
#include "vsc/dm/IDataType.h"

namespace zsp {
namespace be {
namespace sw {

class NameMap;
using NameMapUP=std::unique_ptr<NameMap>;
/**
 * @brief Supports name mangling function and type names
 * 
 */
class NameMap : 
    public virtual INameMap,
    public virtual arl::dm::VisitorBase {
public:
    NameMap();

    virtual ~NameMap();

    virtual bool hasName(vsc::dm::IDataType *type) const override {
        return (m_type_m.find(type) != m_type_m.end());
    }

    virtual bool hasName(arl::dm::IDataTypeFunction *func) const override {
        return (m_func_m.find(func) != m_func_m.end());
    }

    virtual void setName(vsc::dm::IDataType *type, const std::string &name) override;

    virtual void setName(arl::dm::IDataTypeFunction *func, const std::string &name) override;

    virtual const std::string &getName(vsc::dm::IDataType *type) override;

    virtual const std::string &getName(arl::dm::IDataTypeFunction *func) override;

	virtual void visitDataTypeFunction(arl::dm::IDataTypeFunction *t) override;

	virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

private:
    std::string                                                     m_name;
    std::unordered_map<vsc::dm::IDataType *,std::string>            m_type_m;
    std::unordered_map<arl::dm::IDataTypeFunction *,std::string>    m_func_m;

};

}
}
}


