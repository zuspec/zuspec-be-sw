/**
 * FileUtil.h
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
#include <string>

namespace zsp {
namespace be {
namespace sw {



class FileUtil {
public:
    FileUtil();

    virtual ~FileUtil();

    /**
     * Creates all directories in the given path if they don't exist
     * @param path Directory path to create
     * @return true if successful, false otherwise
     */
    static bool mkdirs(const std::string &path);

    /**
     * Checks if the given path exists and is a directory
     * @param path Path to check
     * @return true if path exists and is a directory
     */  
    static bool isdir(const std::string &path);

    /**
     * Checks if the given path exists and is a regular file
     * @param path Path to check
     * @return true if path exists and is a regular file
     */
    static bool isfile(const std::string &path);

};

}
}
}
