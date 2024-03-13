project=byzerevaluation

version=$(grep -oP '__version__ = "\K[0-9]+\.[0-9]+\.[0-9]+' src/byzerevaluation/version.py | cut -d '"' -f 1)
echo "Version: $version"

echo "Clean dist"
rm -rf ./dist/*

echo "Build ${project}"
pip uninstall -y ${project}

echo "Build ${project} ${version}"
python setup.py sdist bdist_wheel
cd ./dist/

echo "Install ${project} ${version}"
pip install ${project}-${version}-py3-none-any.whl && cd -

export MODE=${MODE:-"dev"}

if [[ ${MODE} == "release" ]];then
 git tag v${version}
 git push gitcode v${version}
 echo "Upload ${project} ${version}"
 twine upload dist/*
fi
