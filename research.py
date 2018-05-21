#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os 
import ConfigParser

if __name__ == "__main__":
    configfile=os.path.join(os.path.abspath(os.curdir),'hosts')
    cf = ConfigParser.ConfigParser()
    cf.read(configfile)
    sections = cf.sections()
    for section in sections:
        if re.search('net\w[a-z]*',section ):
           print " net section : %s"%(section)
        else:
           print " general section : %s"%(section)




