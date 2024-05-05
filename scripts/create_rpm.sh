# to be executed from source code root directory
sudo apt install rpm rpmlint rpm-i18n elfutils
rm -rf dist
rm -f *.tar.gz
mkdir -p logs
/usr/bin/env python3 setup.py bdist_rpm # > logs/rpm.log
echo ""
echo "Install with: sudo rpm --nodeps -Uhv dist/`ls dist | grep noarch.rpm`"
echo ""
