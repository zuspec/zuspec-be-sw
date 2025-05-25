/*
 * TaskGenerateTypes.cpp
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
#include "TaskGenerateTypes.h"
#include "TaskGenerateType.h"
#include "Output.h"
#include <fstream>
#include <sys/stat.h>
#include <string.h>
#include <errno.h>


namespace zsp {
namespace be {
namespace sw {


TaskGenerateTypes::TaskGenerateTypes(
    IContext            *ctxt,
    const std::string   &outdir) : m_ctxt(ctxt), m_outdir(outdir) {
    DEBUG_INIT("zsp.be.sw.TaskGenerateTypes", ctxt->getDebugMgr());
}

TaskGenerateTypes::~TaskGenerateTypes() {

}

bool TaskGenerateTypes::mkpath(const std::string &path) {
    mode_t mode = 0755;
    char tmp[1024];
    const char *p = path.c_str();
    size_t len;
    
    snprintf(tmp, sizeof(tmp), "%s", p);
    len = strlen(tmp);
    if (tmp[len - 1] == '/') {
        tmp[len - 1] = 0;
    }

    for (char *p = tmp + 1; *p; p++) {
        if (*p == '/') {
            *p = 0;
            if (mkdir(tmp, mode) != 0) {
                if (errno != EEXIST) {
                    return false;
                }
            }
            *p = '/';
        }
    }
    
    if (mkdir(tmp, mode) != 0) {
        if (errno != EEXIST) {
            return false;
        }
    }
    
    return true;
}

void TaskGenerateTypes::generate(vsc::dm::IDataTypeStruct *root) {
    DEBUG_ENTER("generate %s", root->name().c_str());
    // First, find all types that we need to generate
    m_types.clear();
    root->accept(this);

    // Create the output directory if it doesn't exist
    mkpath(m_outdir);


    // Now, go through and generate them
    for (auto it=m_types.begin(); it!=m_types.end(); it++) {
        vsc::dm::IDataTypeStruct *t = *it;

        std::string name = m_ctxt->nameMap()->getName(t);
        std::ofstream out_h_s(m_outdir + "/" + name + ".h");
        std::ofstream out_c_s(m_outdir + "/" + name + ".c");

        TaskGenerateType(m_ctxt, &out_h_s, &out_c_s).generate(t);
    }
    DEBUG_LEAVE("generate %s", root->name().c_str());
}

void TaskGenerateTypes::visitDataTypeArlStruct(arl::dm::IDataTypeArlStruct *t) {
    DEBUG_ENTER("visitDataTypeArlStruct %s", t->name().c_str());
    visitDataTypeStruct(t);
    DEBUG_LEAVE("visitDataTypeArlStruct");
}

void TaskGenerateTypes::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeStruct %s", t->name().c_str());
    if (m_types.insert(t).second) {
        m_types.insert(t);
        VisitorBase::visitDataTypeStruct(t);
    }
    DEBUG_LEAVE("visitDataTypeStruct");
}

dmgr::IDebug *TaskGenerateTypes::m_dbg = 0;


}
}
}
