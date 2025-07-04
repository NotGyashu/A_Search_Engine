#!/bin/bash

# Install dependencies
./scripts/install_deps.sh

# Build project
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)