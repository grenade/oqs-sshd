Name:           openssh-oqs
Version:        %{?version}%{!?version:0}
Release:        1%{?dist}
Summary:        OQS-enabled OpenSSH under /opt with PQ-only policy
License:        BSD
URL:            https://github.com/open-quantum-safe/openssh
BuildArch:      x86_64
# Target hosts must already have these:
Requires:       liboqs
Requires:       oqsprovider
Requires(post): systemd
Requires(postun): systemd
Requires(post): policycoreutils-python-utils
Requires(post): selinux-policy

%description
Prebuilt OQS-OpenSSH installed under /opt/oqs-openssh-<ver> with a systemd drop-in
to run sshd from /opt. Does not replace /usr/sbin/sshd, so dnf updates won’t overwrite it.
Enforces PQ KEX and PQ signatures (ML-DSA/Dilithium). Uses system liboqs/oqsprovider.

%prep
# nothing

%build
# nothing (we package the prebuilt tree from BUILDROOT/opt/...)

%install
# Bring in staged tree produced by build.sh
mkdir -p %{buildroot}
cp -a %{_sourcedir}/pkgroot/* %{buildroot}/

# systemd service drop-in to point sshd at /opt
mkdir -p %{buildroot}/etc/systemd/system/sshd.service.d
cat > %{buildroot}/etc/systemd/system/sshd.service.d/override.conf <<'EOF'
[Service]
ExecStart=
ExecStart=/opt/oqs-openssh/sbin/sshd -D $OPTIONS
EOF

# PQ-only sshd drop-in; token fixed in %post
mkdir -p %{buildroot}/etc/ssh/sshd_config.d
cat > %{buildroot}/etc/ssh/sshd_config.d/50-pq-only.conf <<'EOF'
# Enforce post-quantum KEX and signatures
KexAlgorithms sntrup761x25519-sha512,sntrup761x25519-sha512@openssh.com,mlkem768x25519-sha256
HostKey /etc/ssh/ssh_host_ml-dsa44_key
HostKeyAlgorithms __OQS_SIG_ALGO__
PubkeyAcceptedAlgorithms __OQS_SIG_ALGO__
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
LogLevel VERBOSE
EOF

%post
# ld cache for /opt (harmless if empty)
echo "/opt/oqs-openssh/lib"   >  /etc/ld.so.conf.d/oqs-openssh.conf
echo "/opt/oqs-openssh/lib64" >> /etc/ld.so.conf.d/oqs-openssh.conf
/sbin/ldconfig || true

# PQ host key if missing
if [ ! -f /etc/ssh/ssh_host_ml-dsa44_key ]; then
  /opt/oqs-openssh/bin/ssh-keygen -t oqs -Oqstype=ml-dsa-44 -f /etc/ssh/ssh_host_ml-dsa44_key -N "" || true
fi

# Detect actual OQS sig token and patch config
ALG="$(/opt/oqs-openssh/bin/ssh -Q key | egrep -m1 'ssh-oqs-(ml-dsa-44|dilithium3)')"
if [ -n "$ALG" ]; then
  sed -i "s|__OQS_SIG_ALGO__|$ALG|g" /etc/ssh/sshd_config.d/50-pq-only.conf
else
  logger -t openssh-oqs "Could not detect OQS signature algo; not enforcing PQ sigs."
  sed -i "s|__OQS_SIG_ALGO__|ssh-ed25519|g" /etc/ssh/sshd_config.d/50-pq-only.conf
fi

# SELinux labels
semanage fcontext -a -t ssh_exec_t "/opt/oqs-openssh(/.*)?" 2>/dev/null || true
restorecon -Rv /opt/oqs-openssh /etc/ssh >/dev/null 2>&1 || true

# Validate config with the new binary; restart if OK
if /opt/oqs-openssh/sbin/sshd -t -f /etc/ssh/sshd_config; then
  systemctl daemon-reload
  systemctl restart sshd || true
else
  logger -t openssh-oqs "sshd config test failed; not restarting."
fi

%postun
if [ $1 -eq 0 ]; then
  rm -f /etc/systemd/system/sshd.service.d/override.conf
  systemctl daemon-reload
  systemctl restart sshd || true
fi

%files
/opt/oqs-openssh*
/etc/systemd/system/sshd.service.d/override.conf
/etc/ssh/sshd_config.d/50-pq-only.conf

%changelog
* Mon Sep 29 2025 You <you@example.com> - %{version}-1
- Initial
