#!/bin/bash

NAME="chatbot_ner"                                              # Name of the application
DJANGODIR=chatbot_ner                                         # Django project directory
SOCKFILE=run/gunicorn.sock                                    # we will communicate using this unix socket
USER=`whoami`                                                   # the user to run as
GROUP=`id -gn`                                                  # the group to run as
NUM_WORKERS=4                                                   # how many worker processes should Gunicorn spawn
DJANGO_SETTINGS_MODULE=chatbot_ner.settings                     # which settings file should Django use
DJANGO_WSGI_MODULE=chatbot_ner.wsgi                             # WSGI module name
PORT=8081
TIMEOUT=600

# echo # Installing virtualenvwrapper"
# pip install -U virtualenvwrapper
# source /usr/local/bin/virtualenvwrapper.sh
# mkvirtualenv chatbotnervenv
# workon chatbotnervenv

# echo "Starting $NAME as `whoami`"
# cd $DJANGODIR
# source /usr/local/bin/virtualenvwrapper.sh
# workon chatbotnervenv

export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
export PYTHONPATH=$DJANGODIR:$PYTHONPATH

# Create the run directory if it doesn't exist
RUNDIR=$(dirname $SOCKFILE)
test -d $RUNDIR || mkdir -p $RUNDIR

pip install -r runtime.txt

echo "copying config & run import data"
cd chatbot_ner/
cp config.example config

cd ..
python initial_setup.py
# Start your Django Unicorn
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)
exec gunicorn ${DJANGO_WSGI_MODULE}:application \
  -b 0.0.0.0:$PORT \
  --name $NAME \
  --workers $NUM_WORKERS \
  --user=$USER --group=$GROUP \
  --log-level=debug \
  --bind=unix:$SOCKFILE \
  --timeout $TIMEOUT \
  --backlog=2048
#  --threads=2
