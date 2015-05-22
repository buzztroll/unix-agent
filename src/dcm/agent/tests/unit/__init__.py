import logging

import dcm.agent.utils as agent_utils


def tearDown():
    msg = agent_utils.build_assertion_exception(logging, "END OF TESTS DUMP")
    print msg
    with open("/tmp/stack_dump", "w") as fptr:
        fptr.write(msg)