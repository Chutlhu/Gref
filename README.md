# Gref
Reference graph visualization


## REQUIRMENTS
[pdf-extract](https://github.com/CrossRef/pdfextract)

Same issue on Ubuntu 15.04 (Linux 3.19.0-31-generic #36-Ubuntu i686)
Thanks msegado for the work around! used the following procedure on a fresh install.

    sudo apt-get install build-essential
    sudo apt-get install ruby-full
    sudo apt-get install zlib1g-dev
    gem install nokogiri
    sudo apt-get install libsqlite3-dev
    sudo gem install specific_install
    sudo gem specific_install https://github.com/EbookGlue/libsvm-ruby-swig.git
    sudo gem install pdf-reader -v 1.1.1
    sudo gem install prawn -v 0.12.0
    sudo gem install pdf-extract
