# nextcloudcmd for Fedora 44

This repository builds the official Nextcloud `nextcloudcmd` target without the desktop GUI,
tests it in a clean Fedora 44 container, and publishes a self-contained dynamic bundle.

The bundle installs below `/opt/nextcloudcmd` and includes the Nextcloud sync libraries, required
runtime libraries, Qt TLS and SQLite plugins, the default exclusion list, and upstream licenses.
It intentionally uses the Fedora 44 glibc, dynamic loader, and CA certificates from the target
system.

## Install

```bash
curl -fsSL https://github.com/safrano9999/NEXTCLOUDCMD_FEDORA44/releases/latest/download/nextcloudcmd-fedora44-x86_64.zip -o /tmp/nextcloudcmd.zip
curl -fsSL https://github.com/safrano9999/NEXTCLOUDCMD_FEDORA44/releases/latest/download/nextcloudcmd-fedora44-x86_64.zip.sha256 -o /tmp/nextcloudcmd.zip.sha256
(cd /tmp && sha256sum -c nextcloudcmd.zip.sha256)
unzip /tmp/nextcloudcmd.zip -d /
ln -sf /opt/nextcloudcmd/bin/nextcloudcmd /usr/local/bin/nextcloudcmd
nextcloudcmd --version
```

## Source

The version in `VERSION` maps directly to the corresponding tag in the
[official Nextcloud desktop repository](https://github.com/nextcloud/desktop).
