#!/bin/bash

set -e

mkdir -p third_party
cd third_party

# Install moodycamel for lock-free concurrency
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

# Try to install lolhtml for streaming HTML parsing
if [ ! -d "lolhtml" ]; then
    # Check if Rust is installed
    if ! command -v cargo &> /dev/null; then
        echo "Installing Rust for lolhtml compilation..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source $HOME/.cargo/env
    fi
    
    git clone https://github.com/cloudflare/lol-html.git lolhtml
    cd lolhtml
    cargo build --release
    cd ..
fi

# Install libcurl dev with HTTP/2 support
sudo apt-get update
sudo apt-get install -y libcurl4-openssl-dev libssl-dev zlib1g-dev