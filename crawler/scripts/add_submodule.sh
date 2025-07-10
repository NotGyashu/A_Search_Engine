#!/bin/bash
set -e

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <git-url> <target-folder-in-third_party>"
    exit 1
fi

GIT_URL=$1
TARGET="third_party/$2"

git submodule add "$GIT_URL" "$TARGET"
git submodule update --init --recursive

echo "✅ Submodule added to $TARGET. Don't forget to commit .gitmodules and the submodule ref!"
