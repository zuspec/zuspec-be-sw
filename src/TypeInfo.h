/**
 * TypeInfo.h
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
#include <vector>
#include <set>
#include "vsc/dm/IDataTypeStruct.h"
#include "vsc/dm/ITypeField.h"

namespace zsp {
namespace be {
namespace sw {



class TypeInfo;
using TypeInfoUP=vsc::dm::UP<TypeInfo>;
class TypeInfo {
public:
    friend class TaskBuildTypeInfo;

    TypeInfo(vsc::dm::IDataTypeStruct *t);

    virtual ~TypeInfo();

    const std::vector<vsc::dm::ITypeField *> &fields() const {
        return m_fields;
    }

    bool isShadowField(vsc::dm::ITypeField *f) const;

    bool addReferencedValType(vsc::dm::IDataTypeStruct *t);

    bool addReferencedRefType(vsc::dm::IDataTypeStruct *t);

    const std::set<vsc::dm::IDataTypeStruct *> &referencedValTypes() const {
        return m_referenced_val_types;
    }
    const std::set<vsc::dm::IDataTypeStruct *> &referencedRefTypes() const {
        return m_referenced_ref_types;
    }

protected:
    // 

    vsc::dm::IDataTypeStruct             *m_type;
    std::vector<vsc::dm::ITypeField *>   m_fields;
    std::vector<vsc::dm::ITypeField *>   m_shadow_fields;
    std::set<vsc::dm::IDataTypeStruct *> m_referenced_ref_types;
    std::set<vsc::dm::IDataTypeStruct *> m_referenced_val_types;


};

}
}
}


