#!/bin/bash
function abort_deploy {
    git stash pop;
    exit 1;
}
function confirm {
    while true; do
        read -p "$1" yn
        case $yn in
            [Yy]* ) break;;
            * ) abort_deploy;;
        esac
    done
}
echo "Check if all your changes have been commited"
echo "Master branch will be deployed to the production server"
confirm "Are you sure you want to deploy?" &&
git stash &&
git checkout master &&
git fetch -t &&
loc=$(git rev-parse HEAD)
orig=$(git rev-parse @{u})
if test "$orig" != "$loc"; then
    echo "Your master branch isn't up-to-date with origin"
    echo "Aborting"
    abort_deploy;
fi
confirm "Are you still sure?" &&
appcfg.py update . -A the-hat -V 3 --oauth2
git tag -f production
git push -t production
git stash pop


