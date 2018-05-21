#!/bin/bash
# wu.wu@hisilicon.com
# 2015.4.3

source ./d05_scripts/server_brdnum_list
D2B=({0..1}{0..1}{0..1}{0..1}{0..1}{0..1}{0..1}{0..1})
test_pcie()
{
    output=$(./bin/busybox devmem $1)
    #echo $output
    if [ "$output"x = ""x ];  then
        echo "can not get output from reading $1"
        return -1
    fi
    # for [5:0] bit test
    low_output=${output: -2}
    ((low_output=16#"$low_output"))
    low_6bit=${D2B[$low_output]}
    low_6bit=${low_6bit: -6}
    if [ $low_6bit != '010001' ]; then
        echo "the pcie of $1 has not linked up"
	echo "the value of low 5 bit are $low_6bit"
        #return -1
    fi

    output=$(./bin/busybox devmem $2)
    
    # for [24:20] bit test
    high_output=${output:3:2}
    ((high_output=16#"$high_output"))
    high_value=${D2B[$high_output]}
    #echo $high_value
    high_5bit=${high_value:3:5}
    if [ "$high_5bit"x != '01000'x ]; then
        echo "the link lane of $2 has been wrong"
	echo "the value of high 5 bit are $high_5bit"
        #return -1
    fi

    # for [19:16] bit test
    middle_output=${output:5:1}
    ((middle_output=16#"$middle_output"))
    middle_value=${D2B[$middle_output]}
    middle_value=${middle_value: -4}
    if [ "$middle_value"x != "0010"x ]; then
        echo "the link speed of $2 has been wrong"
	echo "the value of middle 4 bit are $middle_value"
        return -1
    fi
    echo ""
    return 0
}

test_pcie 0xa00a0728 0xa00a0080
if [ $? -ne 0 ]; then
    echo 'the pcie1 link status is fail'
    exit -1
else
    echo 'the pcie1 link status is succeed'
    . ./d05_scripts/XGE_speed.sh selected_pcie_netcard 3
fi
#test_pcie 0xb0006a18 0xb0090080
#if [ $? -ne 0 ]; then
#    echo 'the pcie2 link status is fail'
#    exit -1
#else
#    echo 'the pcie2 link status is succeed'
#fi

echo "pcie Test Succeed"
exit 0

