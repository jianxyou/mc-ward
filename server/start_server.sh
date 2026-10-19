#!/bin/zsh
cd "$(dirname "$0")"
exec "/Users/jianxin/Library/Application Support/minecraft/runtime/java-runtime-epsilon/mac-os-arm64/java-runtime-epsilon/jre.bundle/Contents/Home/bin/java" -Xms1G -Xmx4G -jar paper.jar nogui
