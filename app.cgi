#!/usr/bin/env python3
import sys
import os
import glob

sys.path.insert(0, os.path.expanduser("~/public_html"))

for p in glob.glob(os.path.expanduser("~/.local/lib/python3*/site-packages")):
    sys.path.insert(0, p)

from learningrec_api import app
from wsgiref.handlers import CGIHandler

CGIHandler().run(app)
