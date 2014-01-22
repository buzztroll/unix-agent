#!/bin/bash

if [ "X$1" == "X-h" ]; then
    echo "Print out state machine diagrams in the current directory"
    exit 0
fi

working_dir=`mktemp -d /tmp/dcm_agentXXXXX`
echo $working_dir

reply_cmd='import dcm.agent.messaging.reply as reply;r = reply.ReplyRPC(None, None, None, None, None);r._sm.mapping_to_digraph()'

python -c "$reply_cmd" > $working_dir/reply.dot

request_cmd='import dcm.agent.messaging.request as request;r = request.RequestRPC(None, None, None);r._sm.mapping_to_digraph()'

python -c "$request_cmd" > $working_dir/request.dot

dot -T png -oreply.png $working_dir/reply.dot
dot -T png -orequest.png $working_dir/request.dot

#rm -rf $working_dir
