#!/bin/bash
set -x
rtc_test()
{
    current_time=` hwclock -r `
    echo "current time is $current_time"
    set_time="2015-03-30 12:00"
    date -s "$set_time"  #&& hwclock -r
    if [ $? -ne 0 ]; then
        echo "Setting the time has been wrong. Maybe reading rtc is wrong."
        return -1
    fi
    hwclock -w
    if [ $? -ne 0 ]; then
        echo 'Set the time wrong. There is wrong with rtc.'
        return -2
    fi
    read_time=$( hwclock -r )
    result=$(echo $read_time | grep 'Mon 30 Mar')
    if [ "$result" == "" ]; then
        echo 'it is different between the set_time and the read_time'
        return -3
    fi
    echo "rtc test succeed"
    return 0
}

rtc_test




