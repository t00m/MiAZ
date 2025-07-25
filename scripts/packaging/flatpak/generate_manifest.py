#!/usr/bin/env python3
import subprocess

p = subprocess.Popen(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, sterr = p.communicate()
branch_name = stdout.decode().strip()

MANIFEST = """{
    "app-id" : "io.github.t00m.MiAZ",
    "runtime" : "org.gnome.Platform",
    "runtime-version" : "47",
    "sdk" : "org.gnome.Sdk",
    "command" : "miaz",
    "finish-args" : [
        "--share=ipc",
        "--device=dri",
        "--socket=fallback-x11",
        "--socket=wayland",
        "--socket=pulseaudio",
        "--share=network",
        "--allow=bluetooth",
        "--socket=cups",
        "--socket=gpg-agent",
        "--socket=pulseaudio",
        "--socket=ssh-auth",
        "--filesystem=host"
    ],
    "cleanup" : [
        "/include",
        "/lib/pkgconfig",
        "/man",
        "/share/doc",
        "/share/gtk-doc",
        "/share/man",
        "/share/pkgconfig",
        "*.la",
        "*.a"
    ],
    "modules" : [
        {
            "name" : "libpeas",
            "buildsystem": "meson",
            "config-opts" : [
                "-Dlua51=false",
                "-Dpython3=true"
            ],
            "cleanup" : [
                "/bin/*",
                "/lib/peas-demo",
                "/lib/libpeas-gtk*"
            ],
            "sources" : [
                {
                    "type" : "git",
                    "url" : "https://gitlab.gnome.org/GNOME/libpeas.git",
                    "tag": "1.36",
                    "commit": "c68ecac0025caa5fa2401deff41d3b1959062600"
                }
            ]
        },
        {
            "name": "python3-requests",
            "buildsystem": "simple",
            "build-commands": [
                "pip3 install --verbose --exists-action=i --no-index --find-links=\\\"file://${PWD}\\\" --prefix=${FLATPAK_DEST} \\\"requests\\\" --no-build-isolation"
            ],
            "sources": [
                {
                    "type": "file",
                    "url": "https://files.pythonhosted.org/packages/38/fc/bce832fd4fd99766c04d1ee0eead6b0ec6486fb100ae5e74c1d91292b982/certifi-2025.1.31-py3-none-any.whl",
                    "sha256": "ca78db4565a652026a4db2bcdf68f2fb589ea80d0be70e03929ed730746b84fe"
                },
                {
                    "type": "file",
                    "url": "https://files.pythonhosted.org/packages/16/b0/572805e227f01586461c80e0fd25d65a2115599cc9dad142fee4b747c357/charset_normalizer-3.4.1.tar.gz",
                    "sha256": "44251f18cd68a75b56585dd00dae26183e102cd5e0f9f1466e6df5da2ed64ea3"
                },
                {
                    "type": "file",
                    "url": "https://files.pythonhosted.org/packages/76/c6/c88e154df9c4e1a2a66ccf0005a88dfb2650c1dffb6f5ce603dfbd452ce3/idna-3.10-py3-none-any.whl",
                    "sha256": "946d195a0d259cbba61165e88e65941f16e9b36ea6ddb97f00452bae8b1287d3"
                },
                {
                    "type": "file",
                    "url": "https://files.pythonhosted.org/packages/f9/9b/335f9764261e915ed497fcdeb11df5dfd6f7bf257d4a6a2a686d80da4d54/requests-2.32.3-py3-none-any.whl",
                    "sha256": "70761cfe03c773ceb22aa2f671b4757976145175cdfca038c02654d061d6dcc6"
                },
                {
                    "type": "file",
                    "url": "https://files.pythonhosted.org/packages/6b/11/cc635220681e93a0183390e26485430ca2c7b5f9d33b15c74c2861cb8091/urllib3-2.4.0-py3-none-any.whl",
                    "sha256": "4e16665048960a0900c702d4a66415956a584919c03361cac9f1df5c5dd7e813"
                }
            ]
        },
        {
            "name" : "miaz",
            "builddir" : true,
            "buildsystem" : "meson",
            "sources" : [
                {
                    "type" : "git",
                    "url" : "https://github.com/t00m/MiAZ.git",
                    "tag" : "%s"
                }
            ]
        }
    ]
}"""

print(MANIFEST % branch_name)
