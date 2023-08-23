#!/bin/bash



# Run this as root to install Feedex on your system

printf "Installing FEEDEX ...\n\n"

sudo mkdir -p "/usr/share/feedex/data"
sudo mkdir -p "/usr/share/feedex/feedex"

# Unpack language models
[[ ! -d ./data/models/de_index ]] && unzip ./data/models/de_index.zip -d ./data/models
[[ ! -d ./data/models/en_index ]] && unzip ./data/models/en_index.zip -d ./data/models
[[ ! -d ./data/models/es_index ]] && unzip ./data/models/es_index.zip -d ./data/models
[[ ! -d ./data/models/fr_index ]] && unzip ./data/models/fr_index.zip -d ./data/models
[[ ! -d ./data/models/pl_index ]] && unzip ./data/models/pl_index.zip -d ./data/models
[[ ! -d ./data/models/ru_index ]] && unzip ./data/models/ru_index.zip -d ./data/models

sudo cp -r ./data "/usr/share/feedex"
sudo cp ./feedex/*.py "/usr/share/feedex/feedex"

sudo cp ./feedex/feedex "/usr/bin/feedex"


sudo cp ./data/examples/config /etc/feedex.conf


if [[ "$1" != "no_gui" ]]; then

    sudo cp ./data/feedex.desktop /usr/share/applications/feedex.desktop
    sudo chmod 655 /usr/share/applications/feedex.desktop
    if [[ ! -d /usr/share/icons/hicolor/symbolic/apps ]]; then
        sudo mkdir /usr/share/icons/hicolor/symbolic/apps
    fi
    sudo cp ./data/icons/*.svg /usr/share/icons/hicolor/symbolic/apps
    sudo chmod 644 /usr/share/icons/hicolor/symbolic/apps/*.svg

fi

sudo chmod 655 /etc/feedex.conf
sudo chmod 755 /usr/bin/feedex
sudo chmod 755 /usr/share/feedex/data/examples/plugins/*.py
sudo find /usr/share/feedex/ -type d -exec chmod 755 {} +
sudo find /usr/share/feedex/ -type f -exec chmod 644 {} +

sudo chmod 755 /usr/share/feedex/data/examples/plugins/*



# Install dependencies
if [[ "$1" != "no_deps" ]]; then

    printf "Installing dependencies ...\n"

    sudo apt-get install python3
    sudo apt-get install pip3
    sudo apt-get install python3-pip
    sudo apt-get install -y python3-feedparser
    sudo apt-get install apt-xapian-index libxapian30 python3-xapian
    sudo apt-get install xapian-bindings

    sudo pip install feedparser
    sudo pip install urllib3
    sudo pip install pysqlite3
    sudo pip install python-dateutil
    sudo pip install snowballstemmer
    sudo pip install Pyphen
    sudo pip install xapian-bingings
    

    if [[ "$1" != "no_gui" ]]; then
        sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
        sudo pip3 install pillow
    fi
fi

printf "\n\nDone...\n"
