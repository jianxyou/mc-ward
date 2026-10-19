#!/bin/zsh
# One-time setup: downloads Paper 26.3 + ViaVersion/ViaBackwards, unpacks the
# Hospital world and accepts the EULA. Run from anywhere:
#   ./server/setup_server.sh
set -e
cd "$(dirname "$0")"

PAPER_URL="https://fill-data.papermc.io/v1/objects/4208a692538104ec88699c0e078b2b89842920a10472ebb37e72cdda27c0d80e/paper-26.3-206.jar"
VIAVERSION_URL="https://cdn.modrinth.com/data/P1OZGk5p/versions/qW2A0Ur2/ViaVersion-5.12.2-SNAPSHOT.jar"
VIABACKWARDS_URL="https://cdn.modrinth.com/data/NpvuJQoq/versions/Rq8nlm3i/ViaBackwards-5.12.2-SNAPSHOT.jar"

[ -f paper.jar ] || { echo "downloading Paper 26.3"; curl -sL "$PAPER_URL" -o paper.jar; }
mkdir -p plugins
[ -f plugins/ViaVersion.jar ]   || { echo "downloading ViaVersion";   curl -sL "$VIAVERSION_URL"   -o plugins/ViaVersion.jar; }
[ -f plugins/ViaBackwards.jar ] || { echo "downloading ViaBackwards"; curl -sL "$VIABACKWARDS_URL" -o plugins/ViaBackwards.jar; }
[ -d Hospital ] || { echo "unpacking Hospital world"; unzip -q Hospital.zip; rm -f Hospital/session.lock; }
echo "eula=true" > eula.txt   # by running this you accept https://aka.ms/MinecraftEULA

# Java 25 is required. The Minecraft launcher ships one; otherwise install Temurin 25
# and put `java` on PATH.
JAVA_LAUNCHER="$HOME/Library/Application Support/minecraft/runtime/java-runtime-epsilon/mac-os-arm64/java-runtime-epsilon/jre.bundle/Contents/Home/bin/java"
if [ -x "$JAVA_LAUNCHER" ]; then JAVA="$JAVA_LAUNCHER"; else JAVA="java"; fi
cat > start_server.sh <<EOF
#!/bin/zsh
cd "\$(dirname "\$0")"
exec "$JAVA" -Xms1G -Xmx4G -jar paper.jar nogui
EOF
chmod +x start_server.sh
echo "done. start with: ./start_server.sh"
