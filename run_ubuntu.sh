#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
. /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != 26.04 ]]; then
    echo "O protocolo exige Ubuntu 26.04. Detectado: $PRETTY_NAME" >&2
    exit 1
fi
out=${1:-resultados_ubuntu}
if [[ -e "$out" || -e "$out.environment.txt" ]]; then
    echo "Escolha uma nova pasta de resultados." >&2
    exit 1
fi
g++ -std=c++20 -O3 -Wall -Wextra -pedantic grasp.cpp -o grasp
{
    printf '%s\n' "$PRETTY_NAME"
    uname -srmo
    lscpu
    free -h
    g++ --version
    python3 --version
    sha256sum grasp.cpp grasp
    echo 'g++ -std=c++20 -O0 -Wall -Wextra -pedantic grasp.cpp -o grasp'
} > "$out.environment.txt"
python3 experiment.py --binary ./grasp --seeds 10 --out "$out"
python3 report.py "$out"
