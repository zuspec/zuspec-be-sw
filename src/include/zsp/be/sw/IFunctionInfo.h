/**
 * IFunctionInfo.h
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
#include "zsp/arl/dm/IDataTypeFunction.h"

namespace zsp {
namespace be {
namespace sw {

enum class FunctionFlags {
    NoFlags = 0,
    Export = (1 << 0),
    Import = (1 << 1)
};

static inline FunctionFlags operator | (const FunctionFlags lhs, const FunctionFlags rhs) {
	return static_cast<FunctionFlags>(
			static_cast<uint32_t>(lhs) | static_cast<uint32_t>(rhs));
}

static inline FunctionFlags operator |= (FunctionFlags &lhs, const FunctionFlags rhs) {
	lhs = static_cast<FunctionFlags>(
			static_cast<uint32_t>(lhs) | static_cast<uint32_t>(rhs));
	return lhs;
}

static inline FunctionFlags operator & (const FunctionFlags lhs, const FunctionFlags rhs) {
	return static_cast<FunctionFlags>(
			static_cast<uint32_t>(lhs) & static_cast<uint32_t>(rhs));
}

static inline FunctionFlags operator ~ (const FunctionFlags lhs) {
	return static_cast<FunctionFlags>(~static_cast<uint32_t>(lhs));
}

class IFunctionInfo;
using IFunctionInfoUP=std::unique_ptr<IFunctionInfo>;
class IFunctionInfo {
public:

    virtual ~IFunctionInfo() { }

    virtual const std::string &getImplName() const = 0;

    virtual void setImplName(const std::string &n) = 0;

    virtual arl::dm::IDataTypeFunction *getDecl() const = 0;

    virtual FunctionFlags getFlags() const = 0;

    virtual void setFlags(FunctionFlags flags) = 0;

};

} /* namespace sw */
} /* namespace be */
} /* namespace zsp */


