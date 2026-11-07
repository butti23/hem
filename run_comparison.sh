#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
. /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != 26.04 ]]; then
    echo "Execute no Ubuntu 26.04." >&2
    exit 1
fi
out=${1:-comparacao_30s}
if [[ -e "$out" || -e "$out.environment.txt" ]]; then
    echo "A pasta escolhida já existe. A bateria não será repetida." >&2
    exit 1
fi
g++ -std=c++20 -O0 -Wall -Wextra -pedantic grasp.cpp -o heuristics
{
    cat /etc/os-release
    uname -srmo
    lscpu
    free -h
    g++ --version
    sha256sum grasp.cpp controls.hpp heuristics
    echo 'g++ -std=c++20 -O0 -Wall -Wextra -pedantic grasp.cpp -o heuristics'
} > "$out.environment.txt"
python3 compare.py --binary ./heuristics --out "$out"
