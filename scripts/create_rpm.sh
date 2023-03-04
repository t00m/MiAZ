# to be executed from source code root directory
rm -rf dist
rm -f *.tar.gz
mkdir -p logs
python setup.py bdist_rpm # > logs/rpm.log
echo ""
echo "Install with: sudo rpm -Uhv dist/`ls dist | grep noarch.rpm`"
echo ""
