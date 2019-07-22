#!/bin/bash

set -eu

# Copyright 2017-Present Pivotal Software, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

pip install -U virtualenvwrapper
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv chatbotnervenv
workon chatbotnervenv
cd chatbot_ner
pip install -r requirements.txt
mkdir -p ~/chatbot_ner_elasticsearch
cd /tmp/
curl -O https://download.elastic.co/elasticsearch/release/org/elasticsearch/distribution/tar/elasticsearch/2.4.4/elasticsearch-2.4.4.tar.gz
tar -xzf elasticsearch-2.4.4.tar.gz -C ~/chatbot_ner_elasticsearch/
~/chatbot_ner_elasticsearch/elasticsearch-2.4.4/bin/elasticsearch -d
cd ~/chatbot_ner/
cp config.example config 
python initial_setup.py
./start_server.sh