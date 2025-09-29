#!/usr/bin/env bash
set -euo pipefail

# inputs
FEDORA_MAJOR=${FEDORA_MAJOR:-40}
PREFIX_BASE=/opt/oqs-openssh

# deps (builder image is Fedora)
dnf -y install git gcc make cmake autoconf automake libtool pkgconfig ninja-build \
  openssl-devel zlib-devel libfido2-devel liboqs-devel rpm-build tar

# build OQS-OpenSSH (link against system /usr OpenSSL and liboqs)
WORKDIR=$(pwd)
BUILDROOT="$WORKDIR/pkgroot"
rm -rf openssh "$BUILDROOT"
git clone --depth=1 https://github.com/open-quantum-safe/openssh.git
cd openssh
export OPENSSL_SYS_DIR=/usr
./oqs-scripts/build_openssh.sh

# stage to /opt/oqs-openssh-<ver>
VER=$(./oqs-test/tmp/bin/ssh -V 2>&1 | awk '{print $1"_"$2}' | tr -d ,)
DEST="$BUILDROOT$PREFIX_BASE-$VER"
mkdir -p "$DEST"
cp -a oqs-test/tmp/* "$DEST"/
ln -sfn "oqs-openssh-$VER" "$BUILDROOT$PREFIX_BASE"

# done; rpmbuild in the workflow using SPECS/openssh-oqs.spec
echo "VERSION=$VER" >> "$GITHUB_OUTPUT" 2>/dev/null || true
