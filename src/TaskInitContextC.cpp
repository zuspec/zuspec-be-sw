/*
 * TaskInitContextC.cpp
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
#include "TaskInitContextC.h"
#include "MethodCallFactoryPrint.h"
#include "MethodCallFactoryRegRw.h"

namespace zsp {
namespace be {
namespace sw {


TaskInitContextC::TaskInitContextC(dmgr::IDebugMgr *dmgr) : m_dmgr(dmgr) {
    DEBUG_INIT("zsp::be::sw::TaskInitContextC", dmgr);

}

TaskInitContextC::~TaskInitContextC() {

}

void TaskInitContextC::init(arl::dm::IContext *ctxt) {
    DEBUG_ENTER("init");
    addMethodCallFactories(ctxt);
    createBackendFuncs(ctxt);
    DEBUG_LEAVE("init");
}

void TaskInitContextC::addMethodCallFactories(arl::dm::IContext *ctxt) {
    DEBUG_ENTER("addMethodCallFactories");
    for (std::vector<arl::dm::IDataTypeFunction *>::const_iterator
        it=ctxt->getDataTypeFunctions().begin();
        it!=ctxt->getDataTypeFunctions().end(); it++) {
        const std::string &name = (*it)->name();
        DEBUG("name: %s", name.c_str());
        int32_t first_colon_idx = name.find("::");
        if (first_colon_idx != -1) {
            std::string pkgname = name.substr(0, first_colon_idx);
            DEBUG("pkgname: %s", pkgname.c_str());

            if (pkgname == "std_pkg") {
                int32_t last_colon = name.rfind("::");
                std::string leafname = name.substr(last_colon+2);
                if (leafname == "print") {
                    (*it)->setAssociatedData(new MethodCallFactoryPrint(m_dmgr));
                }
            } else if (pkgname == "addr_reg_pkg") {
                int32_t next_colon = name.find("::", first_colon_idx+2);
                DEBUG("next_colon: %d first_colon: %d", next_colon, first_colon_idx);
                if (next_colon != -1) {
                    std::string comp_struct_name = name.substr(
                        first_colon_idx+2,
                        next_colon-first_colon_idx-2);
                    int32_t last_colon = name.rfind("::");
                    std::string leaf = name.substr(last_colon+2);
                    DEBUG("leaf: %s", leaf.c_str());
                    if (leaf == "read") {
                        (*it)->setAssociatedData(new MethodCallFactoryRegRw(
                            m_dmgr, false, false));
                    } else if (leaf == "read_val") {
                        (*it)->setAssociatedData(new MethodCallFactoryRegRw(
                            m_dmgr, false, true));
                    } else if (leaf == "write") {
                        (*it)->setAssociatedData(new MethodCallFactoryRegRw(
                            m_dmgr, true, false));
                    } else if (leaf == "write_val") {
                        (*it)->setAssociatedData(new MethodCallFactoryRegRw(
                            m_dmgr, true, true));
                    }
                }
            }
        }
    }
    DEBUG_LEAVE("addMethodCallFactories");
}

void TaskInitContextC::createBackendFuncs(arl::dm::IContext *ctxt) {
    arl::dm::IDataTypeFunction *printf_t = ctxt->mkDataTypeFunction(
        "printf",
        0,
        false,
        arl::dm::DataTypeFunctionFlags::Target);
    ctxt->addDataTypeFunction(printf_t);
}

dmgr::IDebug *TaskInitContextC::m_dbg = 0;

}
}
}
