/**
 * TaskGenerateCompInit.h
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
#include "TaskGenerateStructInit.h"
#include "OutputStr.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateCompInit : public TaskGenerateStructInit {
public:
    TaskGenerateCompInit(IContext *ctxt, TypeInfo *info, IOutput *out_h, IOutput *out_c);

    virtual ~TaskGenerateCompInit();

    virtual void generate_prefix(vsc::dm::IDataTypeStruct *i) override;

    virtual void generate_core(vsc::dm::IDataTypeStruct *i) override;

    virtual void generate_default_init(vsc::dm::IDataTypeStruct *i) override;

	virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;

    virtual const char *default_base_init() const { return "zsp_component_init"; }

private:
    enum class Mode {
        DataFieldInit,
        SubCompInit
    };

private:
    OutputStr           m_subcomp_init;
    Mode                m_mode;

};

}
}
}


