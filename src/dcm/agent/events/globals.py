import dcm.agent.events.callback as events
import dcm.agent.events.pubsub as pubsub

global_space = events.EventSpace()
global_pubsub = pubsub.PubSubEvent(global_space)


class DCMAgentTopics(object):
    CLEANUP = "CLEANUP"
