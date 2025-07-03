from typing import List, Tuple
import numpy as np
import datetime as dt
import calendar

import pandas as pd

from loguru import logger
import os
import sys
import re
import semantic_version

# NOTE: export LOG_LEVEL=DEBUG  <== for debug messages  (default is INFO)
log_level = os.getenv("LOG_LEVEL", "INFO")

# Set up the logger
logger.remove()  # Remove any previously added sinks
logger.add(sys.stdout, level=log_level)

def check_env_compliance(env: str) -> None:
    """
    Check env compliance based on the given environment.
    :param env: The algorithm environment (e.g., "prod/1.13.0", "dev/1.0.0-dev", "exp/1.0.0-exp")
    """

    if env == "local":
        return True
    
    if env == "dev" :
        return True
    
    if env.startswith("exp/"):
        # Check if the experiment has 3 levels of subfolders
        # Ex: exp/ds_user_name/<experiment_name>
        subfolders = env.split("/")

        if len(subfolders) < 3:

            logger.info(f"subfolders: {subfolders}")
            logger.error(f"Invalid exp env: {env}. Valid exp env should match the pattern: exp/ds_user_name/<experiment_name>")

            return False

    # Check if env is in the right format
    elif env.startswith("prod/"):

        # Ensure the env (which is TAG in this context) follows the prod/x.y.z pattern
        msg =  f"{env}\nError: When starting with 'prod/', TAG must follow the pattern prod/x.y.z"
        assert re.match(r'prod/\d+\.\d+\.\d+', env), msg
    
    return True
