import logging
from pyrr import Matrix44


# region projection

def orthographic(w, h):
    return Matrix44.orthogonal_projection(0, w, h, 0, 1, -1, dtype='f4')

# end region projection


# region logger

# create custom logger
logger = logging.getLogger("spectrogram")

# set level - change the commenting on the 2 lines below for more information in your logs
# logger.setLevel(logging.INFO)
logger.setLevel(logging.ERROR)

# create handler
handler = logging.StreamHandler()

# set formatter
log_format = "%(asctime)s - %(levelname)s - %(filename)s - %(message)s"
formatter = logging.Formatter(log_format)
handler.setFormatter(formatter)

# add handler to the logger
logger.addHandler(handler)

# end region logger
