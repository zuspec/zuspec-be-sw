/**
 * TaskCollectSortTypes.h
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
#include <map>
#include <memory>
#include <vector>
#include <set>
#include <functional>
#include "dmgr/IDebugMgr.h"
#include "zsp/arl/dm/IDataTypeComponent.h"
#include "zsp/arl/dm/impl/VisitorBase.h"

namespace zsp {
namespace be {
namespace sw {

class TaskCollectSortTypes;
using TaskCollectSortTypesUP=std::unique_ptr<TaskCollectSortTypes>;
class TaskCollectSortTypes : public arl::dm::VisitorBase {
public:
    TaskCollectSortTypes(dmgr::IDebugMgr *dmgr);

    TaskCollectSortTypes(
        dmgr::IDebugMgr                                         *dmgr,
        const std::function<void (vsc::dm::IDataTypeStruct *)>  &new_type_f);

    virtual ~TaskCollectSortTypes();

    void collect(vsc::dm::IDataTypeStruct *root);

    void sort(
        std::vector<vsc::dm::IDataTypeStruct *>     &types,
        std::vector<arl::dm::IDataTypeFunction *>   &funcs);

	virtual void visitDataTypeAction(arl::dm::IDataTypeAction *t) override;

	virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;

	virtual void visitDataTypeFunction(arl::dm::IDataTypeFunction *t) override;

	virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

	virtual void visitTypeField(vsc::dm::ITypeField *f) override;

	virtual void visitTypeFieldPool(arl::dm::ITypeFieldPool *f) override;

private:

    void enterType(vsc::dm::IDataTypeStruct *t);

    void leaveType();

private:
    static dmgr::IDebug                                 *m_dbg;
    std::function<void (vsc::dm::IDataTypeStruct *)>    m_new_type_f;
    std::map<vsc::dm::IDataTypeStruct *,int32_t>        m_type_m;
    std::vector<vsc::dm::IDataTypeStruct *>             m_type_l;
    std::map<arl::dm::IDataTypeFunction *, int32_t>     m_func_m;
    std::vector<arl::dm::IDataTypeFunction *>           m_func_l;
    std::vector<int32_t>                                m_type_s;
    std::vector<std::set<uint32_t>>                     m_edges;

};

}
}
}


