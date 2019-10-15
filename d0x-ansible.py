#!/usr/bin/env python
# -*- conding:utf-8 -*-
import pdb 
import re
import os
import sys
import time
import pexpect
import getpass
import logging
import datetime
import subprocess
import ConfigParser
from argparse import ArgumentParser



def push_ssh_key():
    '''
    use ansible push ssh key to test host
    :return:
    '''
    #pdb.set_trace()
    configfile=os.path.join(os.path.abspath(os.curdir),'hosts')
    ssh_key_path = os.path.join(os.environ['HOME'], '.ssh', 'id_rsa.pub')
    if not os.path.exists(ssh_key_path):
        os.system("ssh-keygen -t rsa -P '' -f '%s/.ssh/id_rsa'" % os.environ['HOME'])
    try:
        logging.info('Begining to push ssh key for the test host')
        cf = ConfigParser.ConfigParser()
        cf.read(configfile)
        sections = cf.sections()
        for section in sections:
            subprocess.call('ansible-playbook -i hosts push_sshkey.yml -e hosts=%s -u %s' % (section, getpass.getuser()), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        
    except Exception as e:
        logging.debug(e)
        logging.info('push ssh key fail')
        pass

def do_os_test(board_num):
    curpath=os.path.abspath(os.curdir)
    #curlog_file=os.path.join(os.path.abspath(os.curdir),log_file)
    configfile=os.path.join(os.path.abspath(os.curdir),'hosts')
    cf = ConfigParser.ConfigParser()
    cf.read(configfile)
    sections = cf.sections()
    # this place can be modified according to acturally .
    #singlelist=sections[0:3]
    #doublelist=sections[3:]
    #netlist=doublelist[0:len(doublelist)/2] 
    testlist=sections[0:6]
    pdb.set_trace()
    #print "---2 ---curpath : %s sections %s singlelist %s doublelist :%s netlist:%s testlist:%s"%(curpath,sections,singlelist,doublelist,netlist,testlist)
    logging.info("Beginning to run OS Test")
    for section in testlist:
          try: 
              # you must define net info in configfile
              if re.findall('net_[0-9]+s0f0server',section):
                 testdir=os.path.join(curpath ,"roles/iperf/tests")
              else:
                  testdir=os.path.join(curpath,"roles/%s/tests"%(section))
    	      print "cd -testdir: %s"%(testdir)
	      os.chdir(testdir)
    	      #print "---section: %s ---curpath : %s testdir :   %s  curlog :%s"%(section,curpath,testdir, curlog_file)
              storage=os.path.join('/mnt',board_num,section)
    	      print "testdata to be stored in  %s"%(storage)
              #pdb.set_trace()
              #result = subprocess.call('ansible-playbook -i ../../../hosts %s.yml -e dir=%s 2>&1'
              #         % (section ),board_num stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)   
              result = subprocess.call('ansible-playbook -i ../../../hosts %s.yml -e dir=%s 2>&1'
                                % (section, storage), stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)   

    	      print " execute "
              for i in resuly.stdout.readline ():
                  print i
          except Exception as e:
              #logging.debug(e)
              result = e
              pass
    print "---3 ---curpath : %s testdir : %s"%(curpath,testdir)
    #for section in testlist:
    os.chdir(curpath)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Wrong argument, please input the board number."
        sys.exit()
    parser = ArgumentParser()
    parser.add_argument("-N", "--number", action="store", dest="board_num",
                         default="", help="set the board number")

    args = parser.parse_args()
    if args.board_num:
        board_num = args.board_num
    else:
        sys.exit(0)

    #push_ssh_key()
    #Do OS Test
    do_os_test(board_num)
 




