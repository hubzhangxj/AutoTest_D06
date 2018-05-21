#!/bin/bash

# need to modify the scripts to  
cpld_test()
{
    address=$1
    byte=$2
    write_value=$3
    initial_value=$4
    busybox devmem $address $byte

    if [ $? -ne 0 ]; then
        echo 'can not read the register of CPLD'
        return -1
    fi

    old_value=$( ./bin/busybox devmem $address $byte)
    if [ x"$old_value" != x"$initial_value" ]; then
        echo 'the initial value of CPLD is wrong'
	return 1
    fi

    busybox devmem $address $byte $write_value
    if [ $? -ne 0 ]; then
        echo 'there is error when writing the CPLD register'
        return -2
    fi

    new_value=$(./bin/busybox devmem $address $byte)
    #new_value=`expr substr "$new_value" 9 2`
    if [ x"$new_value" != x"$write_value" ]; then
        echo 'setting the register has been wrong'
        return -3
    fi

    busybox devmem $address $byte $initial_value
    echo 'cpld test succeed'
    return 0
}

cpld_test 0x80000005 8 0xAA 0x55

