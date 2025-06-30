/*
 * TaskGenerateModel.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "TaskGatherCompTypes.h"
#include "TaskGenerateModel.h"
#include "FileUtil.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateModel::TaskGenerateModel(
    IContext            *ctxt,
    const std::string   &outdir) : m_ctxt(ctxt), m_outdir(outdir) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateModel", ctxt->getDebugMgr());
}

TaskGenerateModel::~TaskGenerateModel() {

}

void TaskGenerateModel::generate(
    arl::dm::IDataTypeComponent                     *pss_top,
    const std::vector<arl::dm::IDataTypeAction *>   &actions) {
    DEBUG_ENTER("generate");
    std::vector<vsc::dm::IAccept *> actions_l;
//    m_ctxt->setModelName(m_name);

    FileUtil::mkdirs(m_outdir);

    std::vector<arl::dm::IDataTypeComponent *> comp_types;

    TaskGatherCompTypes(m_ctxt).gather(pss_top, comp_types);

    if (!actions.size()) {
        // TODO: go find exported actions
    } else {
        actions_l.insert(
            actions_l.begin(), 
            actions.begin(),
            actions.end());
    }

    // TODO: Generate the import API
    // - Re-iterate core functions for simplicity
    //
    // TODO: Generate library entry-point functions
    // - 

    DEBUG_LEAVE("generate");
}

dmgr::IDebug *TaskGenerateModel::m_dbg = 0;

}
}
}
