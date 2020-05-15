#!/bin/bash

BRANCH="dh-jango"
PYTHON="/home/trommelkreis_v2/opt/python-3.7.7/bin/python3"
MANAGE="/home/trommelkreis_v2/www/manage.py"

printf "Checking out branch %s to ~/www/...\n" $BRANCH
git --work-tree=/home/trommelkreis_v2/www --git-dir=/home/trommelkreis_v2/web.git checkout -f $BRANCH

printf "Collecting static files and migrate database...\n"
if test -f $MANAGE; then
    $PYTHON $MANAGE collectstatic --no-input
    $PYTHON $MANAGE migrate --no-input
fi

printf "Restarting server...\n"
touch /home/trommelkreis_v2/www/tmp/restart.txt

printf "Done\n"