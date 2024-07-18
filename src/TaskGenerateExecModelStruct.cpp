/*
 * TaskGenerateExecModelStruct.cpp
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
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelStruct.h"
#include "TaskGenerateExecModelStructDtor.h"
#include "TaskGenerateExecModelStructInit.h"
#include "TaskGenerateExecModelStructStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelStruct::TaskGenerateExecModelStruct(
    TaskGenerateExecModel   *gen,
    IOutput                 *out_h,
    IOutput                 *out_c) : 
    m_dbg(0), m_gen(gen), m_out_h(out_h), m_out_c(out_c) {

}

TaskGenerateExecModelStruct::~TaskGenerateExecModelStruct() {

}

void TaskGenerateExecModelStruct::generate(vsc::dm::IDataTypeStruct *t) {
    generate_type(t);
    generate_init(t);
    generate_dtor(t);
}

void TaskGenerateExecModelStruct::generate_type(vsc::dm::IDataTypeStruct *t) {
    TaskGenerateExecModelStructStruct(m_gen, m_out_h).generate(t);
}

void TaskGenerateExecModelStruct::generate_init(vsc::dm::IDataTypeStruct *t) {
    TaskGenerateExecModelStructInit(m_gen).generate(t);
}

void TaskGenerateExecModelStruct::generate_dtor(vsc::dm::IDataTypeStruct *t) {
    TaskGenerateExecModelStructDtor(m_gen, m_out_h, m_out_c).generate(t);
}

}
}
}
