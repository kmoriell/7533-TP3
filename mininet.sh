#!/usr/bin/env bash

while getopts h: option
do
case "${option}"
in
h) HEIGHT=$OPTARG;;
esac
done

if [[ -z "${HEIGHT}" ]]; then
    echo "Must set -h option (fat tree height)." 1>&2
    echo "Example: 'sh mininet.sh -h 3'" 1>&2
    exit 1
fi

docker-compose exec --env HEIGHT=${HEIGHT} mininet mn --custom /tmp/topology/example.py --topo example --mac --arp --switch ovsk --controller remote
