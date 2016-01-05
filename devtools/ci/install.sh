MINICONDA=Miniconda3-latest-Linux-x86_64.sh
MINICONDA_MD5=$(curl -s http://repo.continuum.io/miniconda/ | grep -A3 $MINICONDA | sed -n '4p' | sed -n 's/ *<td>\(.*\)<\/td> */\1/p')
wget http://repo.continuum.io/miniconda/$MINICONDA
if [[ $MINICONDA_MD5 != $(md5sum $MINICONDA | cut -d ' ' -f 1) ]]; then  echo "Miniconda MD5 mismatch"; exit 1; fi
bash $MINICONDA -b
export PATH=$HOME/miniconda3/bin:$PATH
conda config --add channels omnia
conda update conda
conda info -a
conda create --yes -n _test python=$TRAVIS_PYTHON_VERSION `cat requirements.txt | xargs`
source activate _test
python -c 'import yaml'
python setup.py install
