/*
 * Output.cpp
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
#include <fstream>
#include <stdarg.h>
#include <stdio.h>
#include "Output.h"


namespace zsp {
namespace be {
namespace sw {


Output::Output(
    std::ostream            *out,
    bool                    owned,
    const std::string       &ind) : m_out(out), m_owned(owned), m_ind(ind) {

}

Output::~Output() {
    if (m_owned) {
        delete m_out;
    }
}


/**
 * @brief Writes indent, content, then a newline
 * 
 * @param fmt 
 * @param ... 
 */
void Output::println(const char *fmt, ...) {
    char tmp[1024];
    va_list ap;
    va_start(ap, fmt);

    int len = vsnprintf(tmp, sizeof(tmp), fmt, ap);
    if (m_ind.size() > 0) {
        m_out->write(m_ind.c_str(), m_ind.size());
    }
    m_out->write(tmp, len);
    m_out->write("\n", 1);

    va_end(ap);
}

/**
 * @brief Writes indent and content without a newline
 * 
 * @param fmt 
 * @param ... 
 */
void Output::print(const char *fmt, ...) {
    char tmp[1024];
    va_list ap;
    va_start(ap, fmt);

    int len = vsnprintf(tmp, sizeof(tmp), fmt, ap);
    if (m_ind.size() > 0) {
        m_out->write(m_ind.c_str(), m_ind.size());
    }
    m_out->write(tmp, len);

    va_end(ap);
}

/**
 * @brief Writes content only
 * 
 * @param fmt 
 * @param ... 
 */
void Output::write(const char *fmt, ...) {
    char tmp[1024];
    va_list ap;
    va_start(ap, fmt);

    int len = vsnprintf(tmp, sizeof(tmp), fmt, ap);
    m_out->write(tmp, len);

    va_end(ap);
}

void Output::close() {
    if (dynamic_cast<std::fstream *>(m_out)) {
        dynamic_cast<std::fstream *>(m_out)->close();
    }
}

/**
 * @brief Writes the current indent
 * 
 */
void Output::indent() {
    if (m_ind.size() > 0) {
        m_out->write(m_ind.c_str(), m_ind.size());
    }
}

void Output::inc_ind() {
    m_ind += "    ";
}

void Output::dec_ind() {
    if (m_ind.size() > 4) {
        m_ind = m_ind.substr(4);
    } else {
        m_ind = "";
    }
}

}
}
}
