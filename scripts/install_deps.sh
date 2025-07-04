#!/bin/bash

set -e

mkdir -p third_party
cd third_party

# Install moodycamel
if [ ! -d "concurrentqueue" ]; then
    git clone https://github.com/cameron314/concurrentqueue.git
fi

# Install gumbo
if [ ! -d "gumbo-parser" ]; then
    git clone https://github.com/google/gumbo-parser.git
    cd gumbo-parser
    ./autogen.sh
    ./configure
    make
    sudo make install
    cd ..
fi

# Install libcurl dev
sudo apt-get install -y libcurl4-openssl-dev