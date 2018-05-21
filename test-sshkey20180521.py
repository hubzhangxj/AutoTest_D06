#!/usr/bin/python
# -*- coding:utf-8 -*-
import pdb

import re
import os
import sys
import yaml
import getpass
import pexpect
import logging
import subprocess
import ConfigParser
from argparse import ArgumentParser

#bmc_ip = "192.168.2.100"
bmc_ip = "192.168.1.151"
bmc_user = "Administrator"
bmc_passwd = "Admin@9000"
#Administrator -P Admin@9000
deactive_sentence = "ipmitool -H %s -I lanplus -U Administrator -P Admin@9000 sol deactivate"
active_command = "ipmitool -H %s -I lanplus -U Administrator -P Admin@9000 sol activate"
reboot_command = "ipmitool -H %s -I lanplus -U Administrator -P Admin@9000 power reset"
poweroff_command = "ipmitool -H %s -I lanplus -U Administrator -P Admin@9000 power off"
reset_BMC_MAC_command = "ipmitool -H %s -I lanplus -U Administrator -P Admin@9000 raw %s %s"  # %S is 0x00 0x18 0x0D 0x05 0x00 0x11
nfs_cmds = "linux /Image_D05 acpi=force pcie_aspm=off rdinit=/init rdinit=/init crashkernel=256M@32M  console=ttyAMA0,115200 earlycon=pl011,mmio,0x602B0000 ip=dhcp"

UEFI_TEST = 1
NFS_TEST = 0
port = 20080

def get_local_ip():
    proc = subprocess.Popen("ip route | grep 192.168 |  awk '{print $(NF-2)}'",
                             shell=True, stdout=subprocess.PIPE)
    (output, returncode) = proc.communicate()
    return output.split('\n')[0]

class Init_board(object):
    def __init__(self, connection_sentence, bmc_ip, board_num, result_log):
        self.connection_sentence = connection_sentence
        self.bmc_ip = bmc_ip
        self.board_num = board_num
        self.local_ip = get_local_ip()
        self.proc = ''
        self.result_log = result_log
        self.bit_nfs = 0

    def _connect_serial(self, test_type):
        if self.proc:
            self.proc.sendline("~.")
        self.proc = pexpect.spawn(self.connection_sentence % (self.bmc_ip))

        usr_home = os.path.expanduser('~')
        d05_log_dir = os.path.join(usr_home, "D05_test")
        if not os.path.exists(d05_log_dir):
	    os.mkdir(d05_log_dir)
        if test_type == 1:
            post_name = 'uefi'
        else:
            post_name = 'nfs'
        logfile = os.path.join(d05_log_dir, "test_for_" + self.board_num +\
                                 '_' + post_name  + ".log")
        if os.path.exists(logfile):
            os.remove(logfile)
        fd = open(logfile, 'w')
        self.proc.logfile = fd
        try:
            self.proc.expect("SOL Session operational")
            #wait_for_prompt(self.proc, "1: 2.4GHz", timeout=50)
        except Exception:
            if re.search(self.proc.before, 
                            "SOL payload already active on another session"):
                self.proc = pexpect.spawn(deactivate_command % (self.bmc_ip))
            self.proc = pexpect.spawn(reboot_command % self.bmc_ip)
            self.proc = pexpect.spawn(self.connection_sentence % (self.bmc_ip))
            #wait_for_prompt(self.proc, "1: 2.4GHz", timeout=50)
        #self.proc.sendline("1")
        #wait_for_prompt(self.proc, "5:DDR 2400Mbps", timeout=200)
        #self.proc.sendline("4")
        index = 1
        while (index != 0):
            index = self.proc.expect(['seconds to stop automatical booting', pexpect.EOF, pexpect.TIMEOUT], 10)
        self.proc.sendline("b")
        wait_for_prompt(self.proc, "Move Highlight", timeout=5)

    def _enter_uefi(self, test_type):
        subprocess.call(reboot_command % self.bmc_ip, shell=True)
        self._connect_serial(test_type)

    def _connect_ipmi(self):
        self.proc = pexpect.spawn(self.connection_sentence % (self.bmc_ip))
        try:
            self.proc.expect("SOL Session operational")
            return True
        except Exception:
            if re.search(self.proc.before, "SOL payload already active on another session"):
                self.proc = pexpect.spawn(deactivate_command % (self.bmc_ip))
                self.proc = pexpect.spawn(self.connection_sentence % (self.bmc_ip))
                self.proc.expect("SOL Session operational")
                return True
        return False
        
    def push_ssh_key(self):
 	'''
	use ansible push ssh key to test host
	:return:
	'''
        configfile=os.path.join(os.path.abspath(os.curdir),'hosts')
        ssh_key_path = os.path.join(os.environ['HOME'], '.ssh', 'id_rsa.pub')
	if not os.path.exists(ssh_key_path):
	    os.system("ssh-keygen -t rsa -P '' -f '%s/.ssh/id_rsa'" % os.environ['HOME'])
        pdb.set_trace()
	try:
	    logging.info('Begining to push ssh key for the test host')
	    cf = ConfigParser.ConfigParser()
	    cf.read(configfile)
	    sections = cf.sections()
            # you must define net info in configfile
            #if re.search('net_ge[0-9]*',):
            #pdb.set_trace()
            #ret=subprocess.Popen("grep -rn server_ip hosts | awk '{print $2}' | cut -c 11- | uniq", shell=True,stdout=subprocess.PIPE );
            #out,err = ret.communicate()
            #serverlist=out.splitlines()
            #sections+=serverlist       
            #pdb.set_trace() 
	    for section in sections:
                   subprocess.call('ansible-playbook -i hosts push_sshkey.yml -e hosts=%s -u %s' % (section, getpass.getuser()), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        
            pdb.set_trace() 
        except Exception as e:
            logging.debug(e)
	    logging.info('push ssh key fail')
	    pass
         
def do_OS_test(init_board):
    configfile=os.path.join(os.path.abspath(os.curdir),'hosts')
    cf = ConfigParser.ConfigParser()
    cf.read(configfile)
    sections = cf.sections()
    print "section list :%s"%(sections)
    pdb.set_trace()
    logging.info("Beginning to run OS Test")
#    for section in sections:
#      if  re.search('net\w[a-z]*',section ): 
#         
#          pattern = re.compile(r"net\w[a-z]*")
#              # Not network server and client.
#              result = subprocess.call('ansible-playbook -i hosts roles/iperf/tests/site.yml >> %s  2>&1'
#                       % (section , log_file), stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
#          
#          
# 
#
#      else:
#          try:
#	      # Not network server and client.
#              result = subprocess.call('ansible-playbook -i hosts roles/%s/tests/site.yml >> %s  2>&1'
#                       % (section , log_file), stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)   
#    
#          except Exception as e:
#              logging.debug(e)
#              result = e
#               pass
#       
#
#    if result:
#        logging.info("Building %s Failed" % section)
#        logging.info("=" * 55)
#        #record_log(log_file, arch, 0)
#    else:
#        logging.info("Building %s Successful" % section)
#        logging.info("=" * 55)
#        #record_log(log_file, arch, 1)

def do_parser(result_log):
    dic = {}
    infp = open(result_log, 'r')
    contents = infp.read()
    for item in re.findall('(.*?) works pass', contents):
        key = item.split()[-1]
        dic[key] = 1
    for item in re.findall('(.*?) works fail', contents):
        key = item.split()[-1]
        dic[key] = 0
    return dic


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

    #log_filename = os.path.join(os.path.expanduser('~'),'D06_test', board_num+'_result.log')
    log_filename = os.path.join(board_num+'_result.log')
    if os.path.exists(log_filename):
        os.remove(log_filename)
    logging_format = '%(asctime)s %(levelname)-5.5s| %(message)s'
    date_format = '%m/%d %H:%M:%S'
    print'logname: %s  debuglevel: %d  log_format: %s date_format: %s'%(log_filename,logging.DEBUG,logging_format,date_format)
    logging.basicConfig(filename=log_filename, level=logging.DEBUG, 
                       format=logging_format, datefmt=date_format)
    
    #pdb.set_trace()
    result_log = logging.getLogger()
    init_board = Init_board(active_command, bmc_ip, board_num, result_log)
    init_board.push_ssh_key()
    print "I am Here"
    
    #remote_ip="192.168.1.159"
    try:
        do_OS_test(init_board)
    except Exception:
        print "the target has hang"
