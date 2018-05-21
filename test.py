#!/usr/bin/python
# -*- coding:utf-8 -*-
import pdb

import re
import os
import sys
import yaml
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

def wait_for_prompt(connection, prompt_pattern, timeout):
    prompt_wait_count = 0
    if timeout == -1:
        timeout = 20
    partial_timeout = timeout / 2.0
    while True:
        try: 
            connection.expect(prompt_pattern, timeout=partial_timeout)
        except pexpect.TIMEOUT:
            if prompt_wait_count < 6:
                logging.warning('Sending newline in case of corruption.')
                prompt_wait_count += 1
                partial_timeout = timeout / 10
                connection.sendline('')
                continue
            else:
                raise
        else:
            break

def get_last_4_bit(board_num):
    board_num_input = int(board_num[-4:])
    last_bit = hex(board_num_input)[2:]
    last_4_bit = last_bit.zfill(4)
    next_to_last_2_bit = last_4_bit[:2].upper()
    last_2_bit = last_4_bit[2:].upper()
    return (next_to_last_2_bit, last_2_bit)

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
        

    def _enter_EBL_cmd(self):
        try:
            self._enter_uefi(UEFI_TEST)
            #self.proc.sendline("\033[B")
            #self.proc.sendline("\033[B")
            #self.proc.sendcontrol("M") 
            #self.proc.sendline("\033[A")
            '''
            进入到一级目录中的Boot Manager选项，按需修改
            '''
            index = 1
            Boot_Manager = 'Boot Manager'
            index = self.proc.expect(['\\x1b\[0m\\x1b\[37m\\x1b\[40m.*%s\\x1b\[0m\\x1b\[30m\\x1b\[47m' % (Boot_Manager), pexpect.EOF, pexpect.TIMEOUT], timeout = 1)
            while (index != 0):
                self.proc.sendline("v")
                index = self.proc.expect(['\\x1b\[0m\\x1b\[37m\\x1b\[40m.*%s\\x1b\[0m\\x1b\[30m\\x1b\[47m' % (Boot_Manager), pexpect.EOF, pexpect.TIMEOUT], timeout = 1)
                print self.proc.before
            time.sleep(1)
            self.proc.sendcontrol('M')
            '''
            进入到二级目录的 EBL 选项，按需修改
            '''
            ebloption = 'Embedded Boot Loader'
            index = self.proc.expect(['\\x1b\[0m\\x1b\[37m\\x1b\[40m.*%s\\x1b\[0m\\x1b\[30m\\x1b\[47m.*' % (ebloption), pexpect.EOF, pexpect.TIMEOUT], timeout = 1)
            while (index != 0):
                self.proc.sendline("v")
                index = self.proc.expect(['\\x1b\[0m\\x1b\[37m\\x1b\[40m.*%s\\x1b\[0m\\x1b\[30m\\x1b\[47m.*' % (ebloption), pexpect.EOF, pexpect.TIMEOUT], timeout = 1)
                print self.proc.before
            self.proc.sendcontrol('M')

            self.proc.expect("D05")
        except Exception:
            self.result_log.info("Enter UEFI fail")
            return False
        else:
            print "Enter UEFI success"
            self.result_log.info("Enter UEFI pass")
            return True


    def set_MAC(self):
        flag = True
        status = self._enter_EBL_cmd()
        print "Set mac testing *****************"
        if status:
            (next_to_last_2_bit, last_2_bit) = get_last_4_bit(self.board_num)
            for i in range(0, 8):   # 6 for 10, 7 for 11
                network_bit_high = i / 6
                network_bit_low = i % 6
                mac_list = ['00', '18', '85', str(network_bit_high) +\
                                    str(network_bit_low), 
                                    next_to_last_2_bit, 
                                    last_2_bit]
                mac_address = "-".join(mac_list)
                try:
                    self.proc.sendline("setmac %s %s" % (mac_address, i))
                    self.proc.expect('MAC:')
                except Exception:
                    flag = False
        else:
            flag = False

        if flag:
            self.result_log.info("setMAC works pass")
        else:
            self.result_log.info("setMAC works fail")
        self.bit_nfs = 1
        return flag

    def show_MAC(self):
        print "show mac testing *****************"
        flag = True
        (next_to_last_2_bit, last_2_bit) = get_last_4_bit(self.board_num)
        for i in range(0, 8):
            network_bit_high = i / 6
            network_bit_low = i % 6
            mac_list = ['00', '18', '85', str(network_bit_high) + \
                            str(network_bit_low), 
                            next_to_last_2_bit,
                            last_2_bit]

            for j in range(0, len(mac_list)):
                if mac_list[j].startswith('0'):
                    mac_list[j] = mac_list[j][1:]
            array2 = [ '0x'+item for item in mac_list ]
            last_str = ' '.join(array2)
            try:
                self.proc.sendline("showmac %s" % i)
                self.proc.expect(last_str)
            except Exception:
                flag = False

        if not flag: 
            self.result_log.info("readMAC works fail")
        else:
            self.result_log.info("readMAC works pass")
        return flag

    def set_board_info(self):
        print "set board info testing *****************"
        try:
            self.proc.sendline("setbrdnum %s" % self.board_num)
            wait_for_prompt(self.proc, "Set board number", timeout=15)
        except Exception:
            self.result_log.info("setBoardNumber works fail")
            return False
        else:
            self.result_log.info("setBoardNumber works pass")
            return True

    def get_board_info(self):
        print "get board info testing *****************"
        try:
            self.proc.sendline("brdinfo")
            wait_for_prompt(self.proc, "D05", timeout=5)
            self.proc.sendcontrol("M")
            wait_for_prompt(self.proc, "D05", timeout=5)
            board_info = self.proc.before
            self.proc.sendline("~.")
        except Exception:
            self.result_log.info("boardinfo works fail")
            return False
        else:
            self.result_log.info(board_info)
            self.result_log.info("boardinfo works pass")
            return True

    def check_SFP_info(self):
        print "check sfp info testing *****************"
        try:
            self.proc.sendline("sfpinfo 1")
            self.proc.expect("D05")
            self.proc.sendline("sfpinfo 2")
            self.proc.expect("D05")
            self.result_log.info(self.proc.before)
            self.proc.sendcontrol("M")
            self.proc.expect("D05")
            self.result_log.info(self.proc.before)
        except Exception:
            self.result_log.info("sfpinfo works fail")
            return False
        else:
            self.result_log.info("sfpinfo works pass")
            return True


    def nfs_boot_board_ip(self):
        print "boot 2p minirootfs info testing *****************"
        remote_ip = ''
        try:
            self._enter_uefi(NFS_TEST)
            ## boot from nfs
            '''
            进入到一级目录中的Boot Manager选项，按需修改
            '''
            index = 1
            Boot_Manager = 'Boot Manager'
            index = self.proc.expect(['\\x1b\[0m\\x1b\[37m\\x1b\[40m.*%s\\x1b\[0m\\x1b\[30m\\x1b\[47m' % (Boot_Manager), pexpect.EOF, pexpect.TIMEOUT], timeout = 1)
            while (index != 0):
                self.proc.sendline("v")
                index = self.proc.expect(['\\x1b\[0m\\x1b\[37m\\x1b\[40m.*%s\\x1b\[0m\\x1b\[30m\\x1b\[47m' % (Boot_Manager), pexpect.EOF, pexpect.TIMEOUT], timeout = 1)
                print self.proc.before
            time.sleep(1)
            self.proc.sendcontrol('M')
            '''
            进入到二级目录的 EFI Network 2 选项，按需修改
            '''
            efinetwork2 = 'EFI Network 2'
            index = self.proc.expect(['\\x1b\[0m\\x1b\[37m\\x1b\[40m.*%s\\x1b\[0m\\x1b\[30m\\x1b\[47m.*' % (efinetwork2), pexpect.EOF, pexpect.TIMEOUT], timeout = 1)
            while (index != 0):
                self.proc.sendline("v")
                index = self.proc.expect(['\\x1b\[0m\\x1b\[37m\\x1b\[40m.*%s\\x1b\[0m\\x1b\[30m\\x1b\[47m.*' % (efinetwork2), pexpect.EOF, pexpect.TIMEOUT], timeout = 1)
                print self.proc.before
            self.proc.sendcontrol('M')

            wait_for_prompt(self.proc, 'Last login', timeout=240)
            wait_for_prompt(self.proc, 'estuary', timeout=20)
            self.proc.sendline("ip addr show `ip route | grep default | awk '{print $NF}'`")
            self.proc.expect('scope global')
            remote_ip_content = self.proc.before
            remote_ip = ''
            find_content = re.findall("(192.168.*?)\/", remote_ip_content)
            if find_content:
                remote_ip = find_content[0]
            self.proc.sendline("~.")
        except Exception:
            self.result_log.info("2p_boot works fail")
            return ''
        else:
            self.result_log.info("2p_boot works pass")
            return remote_ip


def change_caliper_ip(ip, username, passwd):
    conf = ConfigParser.ConfigParser()
    config_file = os.path.join('config', 'client_config.cfg')
    conf.read(config_file)
    conf.set('CLIENT', 'ip', ip)
    conf.set('CLIENT', 'Platform_name', 'D05')
    conf.set('CLIENT', 'port', 22)
    conf.set('CLIENT', 'username', username)
    conf.set('CLIENT', 'password', passwd)
    conf.write(open(config_file, "w"))


def bmc_connect(ip, username, passwd):
    try:
        bmc_conn = pexpect.spawn("ssh %s@%s " % (username, ip))
        index = bmc_conn.expect(['continue connecting (yes/no)?', 'password:'],timeout=100)
	if (index == 0):
            print ' need---------------yes'
            bmc_conn.sendline('yes')
            bmc_conn.expect("(?i)password")
            bmc_conn.sendline(passwd)
	elif(index == 1):
            print ' need---------------passwd'
            bmc_conn.sendline(passwd)
        bmc_conn.expect("Hi1710")
        return bmc_conn
    except Exception:
        bmc_conn.expect("iBMC")
        return bmc_conn
    return ''

def serial_connect(port):
    try:
        serial_connection = pexpect.spawn("telnet localhost %s" % port)
        serial_connection.expect("Escape character")
    except Exception:
        return ''
    #### some operations #####
    return serial_connection

def ipmitool_connect(ip, user, passwd):
    try:
        ipmitool_connection = pexpect.spawn(active_command % (bmc_ip))
        ipmitool_connection.expect("SOL Session operational")
        return ipmitool_connection
    except Exception:
        try:
            if re.search(ipmitool_connection.before, "SOL payload already active on another session"):
                ipmitool_connection = pexpect.spawn(deactivate_command % (bmc_ip))
                ipmitool_connection = pexpect.spawn(connection_sentence % (bmc_ip))
                ipmitool_connection.expect("SOL Session operational")
        except Exception:
            return ''


def check_host_is_bmc_uart(serial_host):
    try:
        serial_host.sendcontrol("M")
        wait_for_prompt(serial_host, 'huawei login:', timeout=5)
        serial_host.sendline("root")
        wait_for_prompt(serial_host, 'Password:', timeout=5)
        serial_host.sendline("Huawei12#$")
        wait_for_prompt(serial_host, 'Hi1710', timeout=20)
        serial_host.sendline("exit")
        serial_host.expect("huawei login:")
        return 1 
    except Exception:
        try:
            serial_host.expect("iBMC")
            serial_host.sendline("exit")
            serial_host.expect("huawei login:")
            return 1
        except Exception:
            return 0
    return 0


def check_host_is_OS_uart(serial_host):
    try:
        serial_host.sendcontrol("M")
        serial_host.sendline("uname")
        wait_for_prompt(serial_host, 'Linux', timeout=5)
    except Exception:
        return 0
    else:
        return 1


def check_ipmitool_os(ipmitool_host):
    try:
        ipmitool_host.sendline('M')
        wait_for_prompt(ipmitool_host, 'estuary', timeout=5)
        ipmitool_host.sendline('M')
        wait_for_prompt(ipmitool_host, 'r', timeout=5)
    except Exception:
        return 0
    else:
        return 1

def check_ipmitool_bmc(ipmitool_host):
    return  check_host_is_bmc_uart(ipmitool_host)


def do_expect_UART(bmc_ssh_host, result_log):
    print "UART testing *****************"
    result1 = result2 = result3 = 0
    try:
        bmc_expect_host.sendline("maint_debug_cli")
        bmc_expect_host.expect("%")
    except Exception:
        result_log.info("UART works fail")
    else:
        bmc_ssh_host.sendline("regwrite 0x16 0")
        bmc_ssh_host.expect("Success")
        serial_host = serial_connect(port)
        ipmi_host = ipmitool_connect(bmc_ip, bmc_user, bmc_passwd)

        result1 = check_host_is_bmc_uart(serial_host)
        result3 = check_ipmitool_os(ipmi_host)
        if not (result1 & result3):
            return 0

        bmc_ssh_host.sendline("regwrite 0x16 1")
        bmc_ssh_host.expect("Success")
        result1 = result2 = result3 = 0
        result1 = check_ipmitool_os(ipmi_host)
        result2 = check_host_is_OS_uart(serial_host)
        result3 = check_ipmitool_bmc(ipmi_host)
        if not (not result1 and result2 and not result3):
            return 0

        bmc_ssh_host.sendline("regwrite 0x16 2")
        bmc_ssh_host.expect("Success")
        result1 = result2 = result3 = 0
        result1 = check_host_is_bmc_uart(serial_host)
        result2 = check_host_is_OS_uart(serial_host)
        result3 = check_ipmitool_os(ipmi_host)
        if not ((not result1) & (not result2) & result3):
            return 0
    return 1


def do_expect_CPU_ME(bmc_expect_host, result_log):
    print "CPU ME testing *****************"
    try:
        bmc_expect_host.sendline("maint_debug_cli")
        bmc_expect_host.expect("%")
    except Exception:
        result_log.info("CPU0_ME works fail")
        result_log.info("CPU1_ME works fail")
    else:
        try:
            bmc_expect_host.sendline("regread 0x10")
            bmc_expect_host.expect("0x80")
            bmc_expect_host.expect("%")
        except Exception:
            result_log.info("CPU0_ME works fail")
        else:
            result_log.info("CPU0_ME works pass")

        try:
            bmc_expect_host.sendline("regread 0x12")
            bmc_expect_host.expect("0x80")
            bmc_expect_host.expect("%")
        except Exception:
            result_log.info("CPU1_ME works fail")
        else:
            result_log.info("CPU1_ME works pass")

def set_light_status(bmc_host, register, value):
    try:
        bmc_expect_host.sendline("maint_debug_cli")
        bmc_expect_host.expect("%")
    except Exception:
        result_log.info("set the light blink fail")
    else:
        try:
            bmc_expect_host.sendline("regwrite %s %s" % (register, value))
            bmc_expect_host.expect("Success")
        except Exception:
            print "set the light status error"
   

def do_OS_test(init_board, remote_ip):
    current_path = os.getcwd()
    caliper_path = os.path.join(current_path, "..", "caliper", "caliper")
    caliper_path = os.path.abspath(caliper_path)

    ## for test running in OS
    if remote_ip:
        print "the remote board ip is %s" % remote_ip
        change_caliper_ip(remote_ip, 'root', 'root')
        if os.path.exists("/home/htsat/.ssh/know_hosts"):
            subprocess.call("rm -fr /home/htsat/.ssh/know_hosts")
        try:
            ssh_expect = pexpect.spawn("ssh-copy-id root@%s"% (remote_ip))
            wait_for_prompt(ssh_expect, "password:", timeout=120)
            ssh_expect.sendline("root")
            ssh_expect.expect("root@%s" % remote_ip)
        except Exception:
            print 'Can not log in the remote target board'
        else:
            print "running caliper *****************"
            try:
                process = subprocess.Popen("%s -f output_%s " % 
                                            (caliper_path, init_board.board_num),
                                            shell=True, stdout=subprocess.PIPE)
                (output, exitcode) = process.communicate()
            except Exception:
                print "The target has been hang"
                process = subprocess.Popen("%s -BRp output_%s " % 
                                            (caliper_path, init_board.board_num),
                                            shell=True, stdout=subprocess.PIPE)
                (output, exitcode) = process.communicate()



def do_UEFI_test(init_board):
    if init_board.set_MAC():
        init_board.show_MAC()
        init_board.check_SFP_info()
    if init_board.set_board_info():
        init_board.get_board_info()


def do_BMC_MAC_test(bmc_expect_host, board_num, result_log):
    try:
        (next_to_last_2_bit, last_2_bit) = get_last_4_bit(board_num)
        bmc_mac_list = ['00', '18', '0D', '05', next_to_last_2_bit, last_2_bit]
        bmc_mac = ':'.join(bmc_mac_list)

        hostmac = ''
        bmc_expect_host.sendline("ifconfig")
        bmc_expect_host.expect("BMC")
        bmc_expect_host.sendline("ifconfig")
        bmc_expect_host.expect("Local Loopback")
        result = bmc_expect_host.before
        if re.findall("HWaddr\s(.*?)", result):
            hostmac = re.findall("Hwaddr\s(.*?)", result)[0]
    except Exception:
        result_log.info("BMC_MAC works fail")
    else:
        if hostmac == bmc_mac:
            result_log.info("BMC_MAC works pass")
        else:
            result_log.info("BMC_MAC works fail")

def do_BMC_test(bmc_expect_host, board_num, result_log, log_filename):
    test_result1 = 0
    do_expect_CPU_ME(bmc_expect_host, result_log)
    
    #do_BMC_MAC_test(bmc_expect_host, board_num, result_log)

    test_result1 = do_expect_UART(bmc_expect_host, log_filename)
    bmc_expect_host.sendline("regwrite 0x15 0")
    bmc_expect_host.expect("Success")
    if test_result1:
        result_log.info("UART_DB9 works pass")
    else:
        result_log.info("UART_DB9 works fail")


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


def write_dic(result_dic, yaml_file):
    fp = open(yaml_file, 'r')
    x = yaml.load(fp)
    # need to done it 
    for item in result_dic:
        if item not in x:
            x[item] = result_dic[item]
    with open(yaml_file, 'w') as outfile:
        outfile.write(yaml.dump(x, default_flow_style=False))
        outfile.close()

def change_bmc_mac(bmc_ip, board_num, result_log):
    (next_to_last_2_bit, last_2_bit) = get_last_4_bit(board_num)
    check_list = [30, 90, 44, 02]
    check_list_1 = ['0x'+str(item) for item in check_list]
    check_code = ' '.join(check_list_1)
    bmc_mac_list = ['00', '18', '0D', '05', next_to_last_2_bit, last_2_bit]
    bmc_mac_list_1 = ['0x'+item for item in bmc_mac_list]
    bmc_mac = ' '.join(bmc_mac_list_1)
    process = subprocess.Popen(reset_BMC_MAC_command % (bmc_ip, check_code, bmc_mac),
                                 shell=True, stdout=subprocess.PIPE)
    (output, exitcode) = process.communicate()
    result_log.info(output)

if __name__ == "__main__":
    print os.path.abspath(os.curdir)
    print " current path %s",(os.getcwd)
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
    pdb.set_trace()
    result_log = logging.getLogger()

    init_board = Init_board(active_command, bmc_ip, board_num, result_log)

    bmc_expect_host = bmc_connect(bmc_ip, bmc_user, bmc_passwd)

    # set the light blink
    #set_light_status(bmc_expect_host, "0xE3", "0x3")
    #set_light_status(bmc_expect_host, "0xE4", "0x77")

    #change_bmc_mac(bmc_ip, board_num, result_log)

    # for UEFI testing
    #do_UEFI_test(init_board)
    #remote_ip = init_board.nfs_boot_board_ip()
    #if not remote_ip:
    #    print 'the 2p booting is failed. Exit the test. Please redo the test.'
    #    sys.exit(0)

    # for test running in BMC
    #do_BMC_test(bmc_expect_host, board_num, result_log, log_filename)

    # for caliper testing
    # add remote_ip temproraily
    remote_ip="192.168.1.217"
    try:
        do_OS_test(init_board, remote_ip)
    except Exception:
        print "the target has hang"

    result_dic = do_parser(log_filename)
    caliper_path = os.path.join(os.getcwd(), "..", "caliper")
    yaml_file = os.path.join(os.path.abspath(caliper_path),
                                'caliper_output',
                                'output_' + board_num,
                                'final_parsing_logs.yaml')
    write_dic(result_dic, yaml_file)

    if not os.path.exists(yaml_file):
        print 'yaml file'
        #set_light_status(bmc_expect_host, "0xE3", "0x02")
        #set_light_status(bmc_expect_host, "0xE4", "0x90")
    else:
        with open(yaml_file, 'r') as contents:
            lines = contents.readlines()
            for line in lines:
                if re.findall('.*\:\s0$', line):
                    #set_light_status(bmc_expect_host, "0xE3", "0x02")
                    #set_light_status(bmc_expect_host, "0xE4", "0x90")
                    print "There is error in the testing"
                    sys.exit(0)
            #set_light_status(bmc_expect_host, "0xE3", "0x03")
            #set_light_status(bmc_expect_host, "0xE4", "0x90")
            print "There is no error in the testing"

