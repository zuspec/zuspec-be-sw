/*
 * FileUtil.cpp
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
#include "FileUtil.h"
#include <sys/stat.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>

namespace zsp {
namespace be {
namespace sw {

FileUtil::FileUtil() {
}

FileUtil::~FileUtil() {
}

bool FileUtil::mkdirs(const std::string &path) {
    char tmp[1024];
    char *p = NULL;
    size_t len;

    if (path.empty()) {
        return false;
    }

    snprintf(tmp, sizeof(tmp), "%s", path.c_str());
    len = strlen(tmp);
    if (tmp[len - 1] == '/') {
        tmp[len - 1] = 0;
    }

    for (p = tmp + 1; *p; p++) {
        if (*p == '/') {
            *p = 0;
            #ifdef _WIN32
            if (mkdir(tmp) != 0 && errno != EEXIST) {
            #else
            if (mkdir(tmp, S_IRWXU) != 0 && errno != EEXIST) {
            #endif
                return false;
            }
            *p = '/';
        }
    }
    #ifdef _WIN32
    if (mkdir(tmp) != 0 && errno != EEXIST) {
    #else
    if (mkdir(tmp, S_IRWXU) != 0 && errno != EEXIST) {
    #endif
        return false;
    }
    return true;
}

bool FileUtil::isdir(const std::string &path) {
    struct stat st;
    if (stat(path.c_str(), &st) == 0) {
        return S_ISDIR(st.st_mode);
    }
    return false;
}

bool FileUtil::isfile(const std::string &path) {
    struct stat st;
    if (stat(path.c_str(), &st) == 0) {
        return S_ISREG(st.st_mode);
    }
    return false;
}

}
}
}
